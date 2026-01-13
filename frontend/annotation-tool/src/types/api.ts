/**
 * APIレスポンス型定義
 * バックエンドのPydanticスキーマに対応
 */

export interface AnnotatorToken {
  access_token: string;
  token_type: string;
}

export interface Annotator {
  id: number;
  username: string;
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

export interface ListFilter {
  status: StatusFilter;
  prefecture_code: string | null;
  vitality_value: number | null;
  page: number;
  per_page: number;
}
