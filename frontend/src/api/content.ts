import api from './index';

// ── 基础类型 ──────────────────────────────────────────────────────
export interface MediaItem {
  id: number;
  title: string;
  overview: string;
  poster_path: string;
  backdrop_path: string;
  release_date: string;
  vote_average: number;
  vote_count: number;
  media_type: 'movie' | 'series';
  genres: string[];
  popularity: number;
  director?: string;
  actors?: string;
  region?: string;
  language?: string;
  duration?: string;
  added_at?: string;
}

export interface MediaListResponse {
  total: number;
  page: number;
  limit: number;
  results: MediaItem[];
}

export interface WatchlistItem {
  id: number;
  user_id: number;
  media_id: number;
  added_at: string;
  media: MediaItem;
}

export interface WatchlistResponse {
  watchlist: MediaItem[];
}

// ── 偏好相关类型 ──────────────────────────────────────────────────
export interface UserPreference {
  id: number;
  user_id: string;
  content_id: string;
  content_type: 'movie' | 'series';
  title: string;
  genres: string;       // 原始字符串，如 "科幻/动作"
  rating: number;
  year: number;
  director: string;
  actors: string;       // 原始字符串，如 "吴京/屈楚萧"
  cover_url?: string;
  comment?: string;
  created_at: string;
}

export interface UserPreferencesResponse {
  preferences: UserPreference[];
}

export interface PreferenceMediaListResponse extends MediaListResponse {
  is_fallback: boolean;  // true 表示无偏好记录，返回的是全量兜底数据
}

// ── API 方法 ──────────────────────────────────────────────────────
export const contentApi = {
  // 获取全量电影列表（未登录或兜底）
  getMovies: async (params?: {
    page?: number;
    limit?: number;
    genre?: string;
    year?: number;
    sort_by?: string;
  }) => {
    const response = await api.get<MediaListResponse>('/movies', { params });
    return response.data;
  },

  // 获取全量剧集列表（未登录或兜底）
  getSeries: async (params?: {
    page?: number;
    limit?: number;
    genre?: string;
    year?: number;
    sort_by?: string;
  }) => {
    const response = await api.get<MediaListResponse>('/series', { params });
    return response.data;
  },

  // 获取基于用户偏好的电影列表（已登录用户）
  getPreferenceMovies: async (userId: number, params?: {
    page?: number;
    limit?: number;
    genre?: string;
    sort_by?: string;
  }) => {
    const response = await api.get<PreferenceMediaListResponse>(
      `/users/${userId}/movies/preference`, { params }
    );
    return response.data;
  },

  // 获取基于用户偏好的剧集列表（已登录用户）
  getPreferenceSeries: async (userId: number, params?: {
    page?: number;
    limit?: number;
    genre?: string;
    sort_by?: string;
  }) => {
    const response = await api.get<PreferenceMediaListResponse>(
      `/users/${userId}/series/preference`, { params }
    );
    return response.data;
  },

  // 获取用户偏好数据（供快捷词条生成和 Agent 上下文使用）
  getUserPreferences: async (userId: number) => {
    const response = await api.get<UserPreferencesResponse>(
      `/users/${userId}/preferences`
    );
    return response.data;
  },

  // 获取电影详情
  getMovieDetails: async (mediaId: number) => {
    const response = await api.get<MediaItem>(`/movies/${mediaId}`);
    return response.data;
  },

  // 获取剧集详情
  getSeriesDetails: async (mediaId: number) => {
    const response = await api.get<MediaItem>(`/series/${mediaId}`);
    return response.data;
  },

  // 搜索媒体
  searchMedia: async (query: string, params?: {
    media_type?: string;
    page?: number;
    limit?: number;
  }) => {
    const response = await api.get<MediaListResponse>('/search', {
      params: { query, ...params }
    });
    return response.data;
  },

  // 获取用户待看清单
  getWatchlist: async (userId: number) => {
    const response = await api.get<WatchlistResponse>(`/users/${userId}/watchlist`);
    return response.data;
  },

  // 添加到待看清单
  addToWatchlist: async (userId: number, mediaId: number) => {
    const response = await api.post(`/users/${userId}/watchlist`, { media_id: mediaId });
    return response.data;
  },

  // 从待看清单移除
  removeFromWatchlist: async (userId: number, mediaId: number) => {
    const response = await api.delete(`/users/${userId}/watchlist/${mediaId}`);
    return response.data;
  },

  // 获取观看历史
  getWatchHistory: async (userId: number) => {
    const response = await api.get<{ history: MediaItem[] }>(`/users/${userId}/history`);
    return response.data;
  },

  // 添加到观看历史
  addToHistory: async (userId: number, mediaId: number) => {
    const response = await api.post(`/users/${userId}/history`, { media_id: mediaId });
    return response.data;
  },

  // 手动添加影视内容
  addContent: async (data: {
    title: string;
    media_type: 'movie' | 'series';
    overview?: string;
    release_date?: string;
    vote_average?: number;
    vote_count?: number;
    popularity?: number;
    poster_path?: string;
    backdrop_path?: string;
    genres?: string[];
  }) => {
    const response = await api.post<{ message: string; media_id: number }>('/content/add', data);
    return response.data;
  },
};
