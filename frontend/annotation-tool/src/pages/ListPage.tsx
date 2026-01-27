/**
 * 一覧画面
 * Requirements: 6.2, 2.1-2.5, 3.1-3.6, 9.1, 9.2
 */

import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import type {
  AnnotationListItem,
  AnnotationStats,
  Prefecture,
  StatusFilter,
  IsReadyFilter,
  BloomStatus,
} from "../types/api";
import {
  BLOOM_STATUS_LABELS,
  ALL_BLOOM_STATUSES,
} from "../types/api";
import {
  getTrees,
  getPrefectures,
  exportCsv,
  updateIsReady,
} from "../api/client";
import { useAuth } from "../hooks/useAuth";

// 日付文字列 → Dateオブジェクト変換
const parseDate = (str: string | null): Date | null => {
  if (!str) return null;
  return new Date(str);
};

// Dateオブジェクト → YYYY-MM-DD文字列変換
const formatDate = (date: Date | null): string | null => {
  if (!date) return null;
  return date.toISOString().split("T")[0];
};

const VITALITY_LABELS: Record<number, string> = {
  1: "とっても元気",
  2: "元気",
  3: "ふつう",
  4: "少し気がかり",
  5: "気がかり",
  [-1]: "診断不可",
};

const STATUS_TABS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "全て" },
  { value: "annotated", label: "入力済み" },
  { value: "unannotated", label: "未入力" },
];

const IS_READY_TABS: { value: IsReadyFilter; label: string }[] = [
  { value: "all", label: "全て" },
  { value: "ready", label: "準備完了" },
  { value: "not_ready", label: "未準備" },
];

// DB値 → スタイルクラス
const getBloomStatusStyle = (status: string | null): string => {
  switch (status) {
    case "before_bloom":
      return "bg-gray-100 text-gray-700";
    case "blooming":
      return "bg-pink-50 text-pink-600";
    case "30_percent":
      return "bg-pink-100 text-pink-700";
    case "50_percent":
      return "bg-pink-200 text-pink-800";
    case "full_bloom":
      return "bg-pink-500 text-white";
    case "falling":
      return "bg-orange-100 text-orange-700";
    case "with_leaves":
      return "bg-lime-100 text-lime-700";
    case "leaves_only":
      return "bg-green-100 text-green-700";
    default:
      return "bg-gray-50 text-gray-500";
  }
};

// 開花状態の日本語ラベルを取得
const getBloomStatusLabel = (status: string | null): string => {
  if (!status) return "未設定";
  return BLOOM_STATUS_LABELS[status as BloomStatus] || "未設定";
};

export function ListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { annotator, logout, isAdmin } = useAuth();

  const [items, setItems] = useState<AnnotationListItem[]>([]);
  const [stats, setStats] = useState<AnnotationStats | null>(null);
  const [prefectures, setPrefectures] = useState<Prefecture[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [updatingIsReady, setUpdatingIsReady] = useState<number | null>(null);

  const status = (searchParams.get("status") as StatusFilter) || "all";
  const prefectureCode = searchParams.get("prefecture_code") || "";
  const vitalityValue = searchParams.get("vitality_value");
  const photoDateFrom = searchParams.get("photo_date_from") || "";
  const photoDateTo = searchParams.get("photo_date_to") || "";
  const isReadyFilter =
    (searchParams.get("is_ready_filter") as IsReadyFilter) || "all";
  const bloomStatusFilter = searchParams.get("bloom_status") || "";
  const page = parseInt(searchParams.get("page") || "1", 10);
  const perPage = 20;

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [treesResponse, prefecturesResponse] = await Promise.all([
        getTrees({
          status,
          prefecture_code: prefectureCode || null,
          vitality_value: vitalityValue ? parseInt(vitalityValue, 10) : null,
          photo_date_from: photoDateFrom || null,
          photo_date_to: photoDateTo || null,
          is_ready_filter: isAdmin ? isReadyFilter || null : null,
          bloom_status: bloomStatusFilter || null,
          page,
          per_page: perPage,
        }),
        getPrefectures(),
      ]);
      setItems(treesResponse.items);
      setStats(treesResponse.stats);
      setTotal(treesResponse.total);
      setPrefectures(prefecturesResponse.prefectures);
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setIsLoading(false);
    }
  }, [
    status,
    prefectureCode,
    vitalityValue,
    photoDateFrom,
    photoDateTo,
    isReadyFilter,
    bloomStatusFilter,
    isAdmin,
    page,
    perPage,
  ]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const updateFilter = (key: string, value: string | null) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    if (key !== "page") {
      newParams.delete("page");
    }
    if (key === "status" && value !== "annotated") {
      newParams.delete("vitality_value");
    }
    setSearchParams(newParams);
  };

  const handleExportCsv = async () => {
    setIsExporting(true);
    try {
      const blob = await exportCsv(true);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "annotations.csv";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("CSV export failed:", error);
      alert("CSVエクスポートに失敗しました");
    } finally {
      setIsExporting(false);
    }
  };

  const handleItemClick = (entireTreeId: number) => {
    const params = new URLSearchParams();
    params.set("status", status);
    if (prefectureCode) params.set("prefecture_code", prefectureCode);
    if (vitalityValue) params.set("vitality_value", vitalityValue);
    if (photoDateFrom) params.set("photo_date_from", photoDateFrom);
    if (photoDateTo) params.set("photo_date_to", photoDateTo);
    if (isReadyFilter && isReadyFilter !== "all") {
      params.set("is_ready_filter", isReadyFilter);
    }
    if (bloomStatusFilter) {
      params.set("bloom_status", bloomStatusFilter);
    }
    navigate(`/annotation/${entireTreeId}?${params}`);
  };

  // is_ready トグル（楽観的更新）
  const handleToggleIsReady = async (
    entireTreeId: number,
    currentIsReady: boolean,
    event: React.MouseEvent
  ) => {
    event.stopPropagation(); // カードのクリックイベントを防止
    if (updatingIsReady !== null) return;

    const newIsReady = !currentIsReady;
    setUpdatingIsReady(entireTreeId);

    // 楽観的更新：UIを即時反映
    setItems((prevItems) =>
      prevItems.map((item) =>
        item.entire_tree_id === entireTreeId
          ? { ...item, is_ready: newIsReady }
          : item
      )
    );

    // 統計情報も楽観的に更新
    if (stats) {
      setStats({
        ...stats,
        ready_count: newIsReady ? stats.ready_count + 1 : stats.ready_count - 1,
        not_ready_count: newIsReady
          ? stats.not_ready_count - 1
          : stats.not_ready_count + 1,
      });
    }

    try {
      await updateIsReady(entireTreeId, newIsReady);
    } catch (error) {
      console.error("Failed to update is_ready:", error);
      // 失敗時にロールバック
      setItems((prevItems) =>
        prevItems.map((item) =>
          item.entire_tree_id === entireTreeId
            ? { ...item, is_ready: currentIsReady }
            : item
        )
      );
      if (stats) {
        setStats({
          ...stats,
          ready_count: currentIsReady
            ? stats.ready_count + 1
            : stats.ready_count - 1,
          not_ready_count: currentIsReady
            ? stats.not_ready_count - 1
            : stats.not_ready_count + 1,
        });
      }
      alert("準備状態の更新に失敗しました");
    } finally {
      setUpdatingIsReady(null);
    }
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-800">
            桜元気度アノテーションツール
          </h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{annotator?.username}</span>
            <button
              onClick={logout}
              className="text-sm text-gray-600 hover:text-gray-800"
            >
              ログアウト
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats */}
        {stats && (
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <div className="flex flex-wrap gap-4 items-center justify-between">
              <div className="flex gap-6 text-sm">
                <span>
                  全件: <strong>{stats.total_count}</strong>
                </span>
                <span>
                  入力済み: <strong>{stats.annotated_count}</strong>
                </span>
                <span>
                  未入力: <strong>{stats.unannotated_count}</strong>
                </span>
                {isAdmin && (
                  <>
                    <span className="text-green-600">
                      準備完了: <strong>{stats.ready_count}</strong>
                    </span>
                    <span className="text-orange-600">
                      未準備: <strong>{stats.not_ready_count}</strong>
                    </span>
                  </>
                )}
              </div>
              <div className="flex gap-3 text-xs">
                {[1, 2, 3, 4, 5, -1].map((v) => {
                  let count: number;
                  switch (v) {
                    case 1: count = stats.vitality_1_count; break;
                    case 2: count = stats.vitality_2_count; break;
                    case 3: count = stats.vitality_3_count; break;
                    case 4: count = stats.vitality_4_count; break;
                    case 5: count = stats.vitality_5_count; break;
                    default: count = stats.vitality_minus1_count;
                  }
                  return (
                    <span key={v} className="px-2 py-1 bg-gray-100 rounded">
                      {VITALITY_LABELS[v]}:{" "}
                      <strong>{count}</strong>
                    </span>
                  );
                })}
              </div>
              <button
                onClick={handleExportCsv}
                disabled={isExporting}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white text-sm rounded-lg transition-colors"
              >
                {isExporting ? "エクスポート中..." : "CSVエクスポート"}
              </button>
            </div>
            {/* 開花状態別統計 */}
            {stats.bloom_status_stats && stats.bloom_status_stats.length > 0 && (
              <div className="w-full mt-4 pt-4 border-t">
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  開花状態別統計
                </h3>
                <div className="flex flex-wrap gap-2">
                  {stats.bloom_status_stats.map((bloomStat) => (
                    <div
                      key={bloomStat.status}
                      className={`px-3 py-2 rounded-lg text-xs ${getBloomStatusStyle(
                        bloomStat.status
                      )}`}
                    >
                      <div className="font-medium">
                        {getBloomStatusLabel(bloomStat.status)}
                      </div>
                      <div className="mt-1 space-x-2">
                        <span>計: {bloomStat.total_count}</span>
                        <span>準備完了: {bloomStat.ready_count}</span>
                        <span>入力済: {bloomStat.annotated_count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center">
            {/* Status Tabs */}
            <div className="flex border rounded-lg overflow-hidden">
              {STATUS_TABS.map((tab) => (
                <button
                  key={tab.value}
                  onClick={() => updateFilter("status", tab.value)}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    status === tab.value
                      ? "bg-sakura-500 text-white"
                      : "bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* is_ready Filter (admin only) */}
            {isAdmin && (
              <div className="flex border rounded-lg overflow-hidden">
                {IS_READY_TABS.map((tab) => (
                  <button
                    key={tab.value}
                    onClick={() =>
                      updateFilter(
                        "is_ready_filter",
                        tab.value === "all" ? null : tab.value
                      )
                    }
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      isReadyFilter === tab.value ||
                      (tab.value === "all" && !isReadyFilter)
                        ? "bg-green-600 text-white"
                        : "bg-white text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            )}

            {/* Prefecture Filter */}
            <select
              value={prefectureCode}
              onChange={(e) =>
                updateFilter("prefecture_code", e.target.value || null)
              }
              className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-sakura-500 focus:border-sakura-500 outline-none"
            >
              <option value="">全ての都道府県</option>
              {prefectures.map((pref) => (
                <option key={pref.code} value={pref.code}>
                  {pref.name}
                </option>
              ))}
            </select>

            {/* Photo Date Range Filter */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">撮影日:</span>
              <DatePicker
                selected={parseDate(photoDateFrom || null)}
                onChange={(date: Date | null) =>
                  updateFilter("photo_date_from", formatDate(date))
                }
                dateFormat="yyyy/MM/dd"
                placeholderText="開始日"
                isClearable
                className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-sakura-500 focus:border-sakura-500 outline-none w-32"
              />
              <span className="text-gray-400">〜</span>
              <DatePicker
                selected={parseDate(photoDateTo || null)}
                onChange={(date: Date | null) =>
                  updateFilter("photo_date_to", formatDate(date))
                }
                dateFormat="yyyy/MM/dd"
                placeholderText="終了日"
                isClearable
                className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-sakura-500 focus:border-sakura-500 outline-none w-32"
              />
            </div>

            {/* Vitality Filter (only for annotated) */}
            {status === "annotated" && (
              <select
                value={vitalityValue || ""}
                onChange={(e) =>
                  updateFilter("vitality_value", e.target.value || null)
                }
                className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-sakura-500 focus:border-sakura-500 outline-none"
              >
                <option value="">全ての元気度</option>
                {[1, 2, 3, 4, 5, -1].map((v) => (
                  <option key={v} value={v}>
                    {VITALITY_LABELS[v]}
                  </option>
                ))}
              </select>
            )}

            {/* 開花状態フィルター */}
            <select
              value={bloomStatusFilter}
              onChange={(e) =>
                updateFilter("bloom_status", e.target.value || null)
              }
              className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-sakura-500 focus:border-sakura-500 outline-none"
            >
              <option value="">全ての開花状態</option>
              {ALL_BLOOM_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {BLOOM_STATUS_LABELS[status]}
                </option>
              ))}
            </select>

            <span className="text-sm text-gray-600 ml-auto">
              該当件数: <strong>{total}</strong>
            </span>
          </div>
        </div>

        {/* Grid */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-sakura-500 border-t-transparent"></div>
            <p className="mt-2 text-gray-600">読み込み中...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow-sm">
            <p className="text-gray-600">該当する画像がありません</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {items.map((item) => (
              <div
                key={item.entire_tree_id}
                onClick={() => handleItemClick(item.entire_tree_id)}
                className="bg-white rounded-lg shadow-sm overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
              >
                <div className="aspect-square relative">
                  <img
                    src={item.thumb_url}
                    alt="桜画像"
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                  {/* Annotation status badge */}
                  {item.annotation_status === "annotated" &&
                    item.vitality_value && (
                      <div className="absolute top-2 right-2 px-2 py-1 bg-sakura-500 text-white text-xs rounded">
                        {VITALITY_LABELS[item.vitality_value]}
                      </div>
                    )}
                  {item.annotation_status === "unannotated" && (
                    <div className="absolute top-2 right-2 px-2 py-1 bg-gray-500 text-white text-xs rounded">
                      未入力
                    </div>
                  )}
                  {/* is_ready badge (admin only) */}
                  {isAdmin && (
                    <div
                      className={`absolute top-2 left-2 px-2 py-1 text-white text-xs rounded ${
                        item.is_ready ? "bg-green-600" : "bg-orange-500"
                      }`}
                    >
                      {item.is_ready ? "準備完了" : "未準備"}
                    </div>
                  )}
                  {/* 開花状態バッジ */}
                  <div
                    className={`absolute bottom-2 left-2 px-2 py-0.5 text-xs rounded ${getBloomStatusStyle(
                      item.bloom_status
                    )}`}
                  >
                    {getBloomStatusLabel(item.bloom_status)}
                  </div>
                </div>
                <div className="p-2">
                  <div className="flex justify-between items-center">
                    <p className="text-xs text-gray-600 truncate flex-1">
                      {item.prefecture_name} - {item.location}
                    </p>
                    {/* is_ready toggle (admin only) */}
                    {isAdmin && (
                      <button
                        onClick={(e) =>
                          handleToggleIsReady(
                            item.entire_tree_id,
                            item.is_ready,
                            e
                          )
                        }
                        disabled={updatingIsReady === item.entire_tree_id}
                        className={`ml-2 relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-1 ${
                          item.is_ready ? "bg-green-600" : "bg-gray-300"
                        } ${
                          updatingIsReady === item.entire_tree_id
                            ? "opacity-50"
                            : ""
                        }`}
                        title={
                          item.is_ready ? "準備完了を解除" : "準備完了にする"
                        }
                      >
                        <span
                          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                            item.is_ready ? "translate-x-4" : "translate-x-0"
                          }`}
                        />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-6">
            <button
              onClick={() => updateFilter("page", String(page - 1))}
              disabled={page <= 1}
              className="px-4 py-2 border rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              前へ
            </button>
            <span className="px-4 py-2 text-sm">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => updateFilter("page", String(page + 1))}
              disabled={page >= totalPages}
              className="px-4 py-2 border rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              次へ
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
