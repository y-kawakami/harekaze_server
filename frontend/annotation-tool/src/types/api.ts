/**
 * APIレスポンス型定義
 * バックエンドのPydanticスキーマに対応
 */

export interface AnnotatorToken {
  access_token: string;
  token_type: string;
}

export type AnnotatorRole = 'admin' | 'annotator';

export interface Annotator {
  id: number;
  username: string;
  role: AnnotatorRole;
  last_login: string | null;
  created_at: string;
}

export interface AnnotationListItem {
  entire_tree_id: number;
  tree_id: number;
  thumb_url: string;
  prefecture_name: string;
  location: string;
  annotation_status: 'annotated' | 'unannotated';
  vitality_value: number | null;
  is_ready: boolean;
  bloom_status: string | null;
}

// DB保存用の英語キー
export type BloomStatus =
  | 'before_bloom'
  | 'blooming'
  | '30_percent'
  | '50_percent'
  | 'full_bloom'
  | 'falling'
  | 'with_leaves'
  | 'leaves_only';

// UI表示用マッピング
export const BLOOM_STATUS_LABELS: Record<BloomStatus, string> = {
  before_bloom: '開花前',
  blooming: '開花',
  '30_percent': '3分咲き',
  '50_percent': '5分咲き',
  full_bloom: '8分咲き（満開）',
  falling: '散り始め',
  with_leaves: '花＋若葉（葉桜）',
  leaves_only: '葉のみ',
};

// 全ての開花ステータス（フィルター用）
export const ALL_BLOOM_STATUSES: BloomStatus[] = [
  'before_bloom',
  'blooming',
  '30_percent',
  '50_percent',
  'full_bloom',
  'falling',
  'with_leaves',
  'leaves_only',
];

// 開花状態別統計
export interface BloomStatusStats {
  status: string;
  total_count: number;
  ready_count: number;
  annotated_count: number;
}

export interface AnnotationStats {
  total_count: number;
  annotated_count: number;
  unannotated_count: number;
  vitality_1_count: number;
  vitality_2_count: number;
  vitality_3_count: number;
  vitality_4_count: number;
  vitality_5_count: number;
  vitality_minus1_count: number;
  ready_count: number;
  not_ready_count: number;
  bloom_status_stats: BloomStatusStats[];
}

export interface AnnotationListResponse {
  items: AnnotationListItem[];
  stats: AnnotationStats;
  total: number;
  page: number;
  per_page: number;
}

export interface AnnotationDetail {
  entire_tree_id: number;
  tree_id: number;
  image_url: string;
  photo_date: string | null;
  prefecture_name: string;
  location: string;
  flowering_date: string | null;
  full_bloom_start_date: string | null;
  full_bloom_end_date: string | null;
  current_vitality_value: number | null;
  current_index: number;
  total_count: number;
  prev_id: number | null;
  next_id: number | null;
  is_ready: boolean;
  bloom_status: string | null;
}

export interface SaveAnnotationResponse {
  entire_tree_id: number;
  vitality_value: number;
  annotated_at: string;
  annotator_id: number;
}

export interface Prefecture {
  code: string;
  name: string;
}

export interface PrefectureListResponse {
  prefectures: Prefecture[];
}

export type StatusFilter = 'all' | 'annotated' | 'unannotated';

export type IsReadyFilter = 'all' | 'ready' | 'not_ready';

export interface ListFilter {
  status: StatusFilter;
  prefecture_code: string | null;
  vitality_value: number | null;
  photo_date_from: string | null;
  photo_date_to: string | null;
  page: number;
  per_page: number;
  is_ready_filter: IsReadyFilter | null;
  bloom_status: string | null;
}

// is_ready 更新用リクエスト/レスポンス型
export interface UpdateIsReadyRequest {
  is_ready: boolean;
}

export interface UpdateIsReadyResponse {
  entire_tree_id: number;
  is_ready: boolean;
  updated_at: string;
}

export interface UpdateIsReadyBatchRequest {
  entire_tree_ids: number[];
  is_ready: boolean;
}

export interface UpdateIsReadyBatchResponse {
  updated_count: number;
  updated_ids: number[];
}
