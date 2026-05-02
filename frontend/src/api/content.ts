import api from './index';

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
  watchlist: WatchlistItem[];
}

export const contentApi = {
  // 获取电影列表
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

  // 获取剧集列表
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
    const response = await api.get<{ history: any[] }>(`/users/${userId}/history`);
    return response.data;
  },

  // 添加到观看历史
  addToHistory: async (userId: number, mediaId: number) => {
    const response = await api.post(`/users/${userId}/history`, { media_id: mediaId });
    return response.data;
  },
};