/**
 * アノテーション画面
 * Requirements: 6.1, 6.2, 6.3, 6.4, 4.1-4.6, 5.1-5.7
 */

import { useState, useEffect, useCallback } from "react";
import {
  useParams,
  useNavigate,
  useSearchParams,
  Link,
} from "react-router-dom";
import type { AnnotationDetail, StatusFilter } from "../types/api";
import { getTreeDetail, saveAnnotation, updateIsReady } from "../api/client";
import { useAuth } from "../hooks/useAuth";

const VITALITY_OPTIONS: { value: number; label: string; color: string }[] = [
  { value: 1, label: "とっても元気", color: "bg-green-500" },
  { value: 2, label: "元気", color: "bg-lime-500" },
  { value: 3, label: "ふつう", color: "bg-yellow-500" },
  { value: 4, label: "少し気がかり", color: "bg-orange-500" },
  { value: 5, label: "気がかり", color: "bg-red-500" },
  { value: -1, label: "診断不可", color: "bg-gray-500" },
];

export function AnnotationPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { annotator, logout, isAdmin } = useAuth();

  const [detail, setDetail] = useState<AnnotationDetail | null>(null);
  const [selectedValue, setSelectedValue] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [isUpdatingIsReady, setIsUpdatingIsReady] = useState(false);
  const [isReadyMessage, setIsReadyMessage] = useState<string | null>(null);

  const status = (searchParams.get("status") as StatusFilter) || "all";
  const prefectureCode = searchParams.get("prefecture_code") || "";
  const vitalityValue = searchParams.get("vitality_value");
  const photoDateFrom = searchParams.get("photo_date_from") || "";
  const photoDateTo = searchParams.get("photo_date_to") || "";
  const isReadyFilter =
    (searchParams.get("is_ready_filter") as "all" | "ready" | "not_ready") ||
    "all";

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const result = await getTreeDetail(parseInt(id, 10), {
        status,
        prefecture_code: prefectureCode || null,
        vitality_value: vitalityValue ? parseInt(vitalityValue, 10) : null,
        photo_date_from: photoDateFrom || null,
        photo_date_to: photoDateTo || null,
        is_ready_filter: isReadyFilter,
      });
      setDetail(result);
      setSelectedValue(result.current_vitality_value);
    } catch (error) {
      console.error("Failed to fetch detail:", error);
    } finally {
      setIsLoading(false);
    }
  }, [
    id,
    status,
    prefectureCode,
    vitalityValue,
    photoDateFrom,
    photoDateTo,
    isReadyFilter,
  ]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleSave = async (value: number) => {
    if (!id) return;
    setSelectedValue(value);
    setIsSaving(true);
    setSaveMessage(null);

    try {
      await saveAnnotation(parseInt(id, 10), value);
      setSaveMessage("保存しました");
      setTimeout(() => setSaveMessage(null), 2000);
    } catch (error) {
      console.error("Failed to save:", error);
      setSaveMessage("保存に失敗しました");
    } finally {
      setIsSaving(false);
    }
  };

  const navigateTo = (targetId: number | null) => {
    if (!targetId) return;
    const params = new URLSearchParams();
    params.set("status", status);
    if (prefectureCode) params.set("prefecture_code", prefectureCode);
    if (vitalityValue) params.set("vitality_value", vitalityValue);
    if (photoDateFrom) params.set("photo_date_from", photoDateFrom);
    if (photoDateTo) params.set("photo_date_to", photoDateTo);
    if (isReadyFilter && isReadyFilter !== "all") {
      params.set("is_ready_filter", isReadyFilter);
    }
    navigate(`/annotation/${targetId}?${params}`);
  };

  const getBackUrl = () => {
    const params = new URLSearchParams();
    params.set("status", status);
    if (prefectureCode) params.set("prefecture_code", prefectureCode);
    if (vitalityValue) params.set("vitality_value", vitalityValue);
    if (photoDateFrom) params.set("photo_date_from", photoDateFrom);
    if (photoDateTo) params.set("photo_date_to", photoDateTo);
    if (isReadyFilter && isReadyFilter !== "all") {
      params.set("is_ready_filter", isReadyFilter);
    }
    return `/?${params}`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString("ja-JP");
  };

  const formatDateShort = (dateStr: string | null) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };

  const getBloomStatusStyle = (status: string | null) => {
    switch (status) {
      case "開花前":
        return "bg-gray-100 text-gray-700";
      case "3分咲き":
        return "bg-pink-100 text-pink-700";
      case "5分咲き":
        return "bg-pink-200 text-pink-800";
      case "満開":
        return "bg-pink-500 text-white";
      case "散り始め":
        return "bg-orange-100 text-orange-700";
      case "葉桜":
        return "bg-green-100 text-green-700";
      default:
        return "bg-gray-50 text-gray-500";
    }
  };

  // is_ready トグルハンドラ（管理者専用）
  const handleToggleIsReady = async () => {
    if (!id || !detail || isUpdatingIsReady) return;

    const newIsReady = !detail.is_ready;
    setIsUpdatingIsReady(true);
    setIsReadyMessage(null);

    // 楽観的更新
    setDetail((prev) => (prev ? { ...prev, is_ready: newIsReady } : prev));

    try {
      await updateIsReady(parseInt(id, 10), newIsReady);
      setIsReadyMessage("準備状態を保存しました");
      setTimeout(() => setIsReadyMessage(null), 2000);
    } catch (error) {
      console.error("Failed to update is_ready:", error);
      // ロールバック
      setDetail((prev) => (prev ? { ...prev, is_ready: !newIsReady } : prev));
      setIsReadyMessage("準備状態の保存に失敗しました");
    } finally {
      setIsUpdatingIsReady(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-sakura-500 border-t-transparent"></div>
          <p className="mt-2 text-gray-600">読み込み中...</p>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-gray-600">画像が見つかりません</p>
          <Link
            to="/"
            className="text-sakura-500 hover:underline mt-2 inline-block"
          >
            一覧に戻る
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link
              to={getBackUrl()}
              className="text-sakura-500 hover:text-sakura-600 font-medium"
            >
              &larr; データ一覧リストへ
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600 font-medium">
              {detail.current_index + 1} / {detail.total_count}
            </span>
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
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Image */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm overflow-hidden">
              <img
                src={detail.image_url}
                alt="桜画像"
                className="w-full h-auto max-h-[70vh] object-contain bg-gray-100"
              />
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Vitality Selection */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-bold text-gray-800 mb-4">
                元気度入力
              </h2>
              <div className="space-y-2">
                {VITALITY_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleSave(option.value)}
                    disabled={isSaving}
                    className={`w-full py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-between ${
                      selectedValue === option.value
                        ? `${option.color} text-white shadow-lg scale-[1.02]`
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    <span>{option.label}</span>
                    <span className="text-sm opacity-75">({option.value})</span>
                  </button>
                ))}
              </div>
              {saveMessage && (
                <p
                  className={`mt-4 text-center text-sm ${
                    saveMessage.includes("失敗")
                      ? "text-red-500"
                      : "text-green-500"
                  }`}
                >
                  {saveMessage}
                </p>
              )}
            </div>

            {/* Photo Info */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-bold text-gray-800 mb-4">撮影情報</h2>
              <dl className="space-y-3 text-md">
                <div className="flex justify-between items-center">
                  <dt className="text-gray-500">開花状態</dt>
                  <dd>
                    <span
                      className={`px-2 py-0.5 text-sm rounded font-medium ${getBloomStatusStyle(
                        detail.bloom_status
                      )}`}
                    >
                      {detail.bloom_status || "-"}
                    </span>
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">撮影日</dt>
                  <dd className="text-gray-800">
                    {formatDate(detail.photo_date)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">開花日</dt>
                  <dd className="text-gray-800">
                    {formatDateShort(detail.flowering_date)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">満開開始日</dt>
                  <dd className="text-gray-800">
                    {formatDateShort(detail.full_bloom_start_date)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">満開終了日</dt>
                  <dd className="text-gray-800">
                    {formatDateShort(detail.full_bloom_end_date)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">都道府県</dt>
                  <dd className="text-gray-800">{detail.prefecture_name}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">撮影場所</dt>
                  <dd className="text-gray-800">{detail.location || "-"}</dd>
                </div>
                {/* is_ready 状態表示とトグル（管理者のみ） */}
                {isAdmin && (
                  <div className="flex justify-between items-center pt-2 border-t mt-2">
                    <dt className="text-gray-500">準備状態</dt>
                    <dd className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 text-xs rounded ${
                          detail.is_ready
                            ? "bg-green-100 text-green-700"
                            : "bg-orange-100 text-orange-700"
                        }`}
                      >
                        {detail.is_ready ? "準備完了" : "未準備"}
                      </span>
                      <button
                        onClick={handleToggleIsReady}
                        disabled={isUpdatingIsReady}
                        className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-1 ${
                          detail.is_ready ? "bg-green-600" : "bg-gray-300"
                        } ${
                          isUpdatingIsReady
                            ? "opacity-50 cursor-not-allowed"
                            : ""
                        }`}
                        title={
                          detail.is_ready ? "準備完了を解除" : "準備完了にする"
                        }
                      >
                        <span
                          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                            detail.is_ready ? "translate-x-4" : "translate-x-0"
                          }`}
                        />
                      </button>
                    </dd>
                  </div>
                )}
              </dl>
              {/* is_ready 保存メッセージ */}
              {isReadyMessage && (
                <p
                  className={`mt-3 text-center text-sm ${
                    isReadyMessage.includes("失敗")
                      ? "text-red-500"
                      : "text-green-500"
                  }`}
                >
                  {isReadyMessage}
                </p>
              )}
            </div>

            {/* Navigation */}
            <div className="flex gap-3">
              <button
                onClick={() => navigateTo(detail.prev_id)}
                disabled={!detail.prev_id}
                className="flex-1 py-3 px-4 border rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
              >
                &larr; 戻る
              </button>
              <button
                onClick={() => navigateTo(detail.next_id)}
                disabled={!detail.next_id}
                className="flex-1 py-3 px-4 bg-sakura-500 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-sakura-600 transition-colors"
              >
                次へ &rarr;
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
