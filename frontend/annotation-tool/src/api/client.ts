/**
 * APIクライアント
 * アノテーションAPIへのHTTPリクエストを管理
 */

import type {
  AnnotatorToken,
  Annotator,
  AnnotationListResponse,
  AnnotationDetail,
  SaveAnnotationResponse,
  PrefectureListResponse,
  ListFilter,
} from '../types/api';

const API_BASE = '/annotation_api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('annotation_token');
  if (!token) {
    return {};
  }
  return {
    Authorization: `Bearer ${token}`,
  };
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('annotation_token');
      window.location.href = '/login';
    }
    const message = await response.text();
    throw new ApiError(response.status, message);
  }
  return response.json();
}

export async function login(
  username: string,
  password: string
): Promise<AnnotatorToken> {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const response = await fetch(`${API_BASE}/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  });

  return handleResponse<AnnotatorToken>(response);
}

export async function getMe(): Promise<Annotator> {
  const response = await fetch(`${API_BASE}/me`, {
    headers: getAuthHeaders(),
  });

  return handleResponse<Annotator>(response);
}

export async function getTrees(
  filter: Partial<ListFilter>
): Promise<AnnotationListResponse> {
  const params = new URLSearchParams();
  if (filter.status) params.append('status', filter.status);
  if (filter.prefecture_code) params.append('prefecture_code', filter.prefecture_code);
  if (filter.vitality_value !== undefined && filter.vitality_value !== null) {
    params.append('vitality_value', String(filter.vitality_value));
  }
  if (filter.photo_date_from) params.append('photo_date_from', filter.photo_date_from);
  if (filter.photo_date_to) params.append('photo_date_to', filter.photo_date_to);
  if (filter.page) params.append('page', String(filter.page));
  if (filter.per_page) params.append('per_page', String(filter.per_page));

  const response = await fetch(`${API_BASE}/trees?${params}`, {
    headers: getAuthHeaders(),
  });

  return handleResponse<AnnotationListResponse>(response);
}

export async function getTreeDetail(
  entireTreeId: number,
  filter: Partial<ListFilter>
): Promise<AnnotationDetail> {
  const params = new URLSearchParams();
  if (filter.status) params.append('status', filter.status);
  if (filter.prefecture_code) params.append('prefecture_code', filter.prefecture_code);
  if (filter.vitality_value !== undefined && filter.vitality_value !== null) {
    params.append('vitality_value', String(filter.vitality_value));
  }
  if (filter.photo_date_from) params.append('photo_date_from', filter.photo_date_from);
  if (filter.photo_date_to) params.append('photo_date_to', filter.photo_date_to);

  const response = await fetch(`${API_BASE}/trees/${entireTreeId}?${params}`, {
    headers: getAuthHeaders(),
  });

  return handleResponse<AnnotationDetail>(response);
}

export async function saveAnnotation(
  entireTreeId: number,
  vitalityValue: number
): Promise<SaveAnnotationResponse> {
  const response = await fetch(`${API_BASE}/trees/${entireTreeId}/annotation`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ vitality_value: vitalityValue }),
  });

  return handleResponse<SaveAnnotationResponse>(response);
}

export async function getPrefectures(): Promise<PrefectureListResponse> {
  const response = await fetch(`${API_BASE}/prefectures`, {
    headers: getAuthHeaders(),
  });

  return handleResponse<PrefectureListResponse>(response);
}

export async function exportCsv(includeUndiagnosable: boolean = true): Promise<Blob> {
  const params = new URLSearchParams();
  params.append('include_undiagnosable', String(includeUndiagnosable));

  const response = await fetch(`${API_BASE}/export/csv?${params}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new ApiError(response.status, 'CSVエクスポートに失敗しました');
  }

  return response.blob();
}
