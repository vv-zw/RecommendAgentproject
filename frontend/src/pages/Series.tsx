import React, { useState, useEffect } from 'react';
import { Tv, Filter, SortAsc, Plus, ChevronLeft, ChevronRight, Info } from 'lucide-react';
import { Link } from 'react-router-dom';
import MediaGrid from '../components/media/MediaGrid';
import Button from '../components/common/Button';
import { contentApi, MediaItem } from '../api/content';
import { useAuthStore } from '../store/authStore';

const GENRES = ['全部', '剧情', '喜剧', '爱情', '悬疑', '惊悚', '科幻', '奇幻', '动作', '历史', '犯罪', '动画'];
const SORT_OPTIONS = [
  { label: '热度排序', value: 'popularity.desc' },
  { label: '评分排序', value: 'vote_average.desc' },
  { label: '最新上映', value: 'release_date.desc' },
];

const Series: React.FC = () => {
  const { isAuthenticated, user } = useAuthStore();
  const [series, setSeries] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFallback, setIsFallback] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [genre, setGenre] = useState('全部');
  const [sortBy, setSortBy] = useState('popularity.desc');
  const [watchlistIds, setWatchlistIds] = useState<number[]>([]);
  const limit = 20;

  // 获取剧集列表：已登录调用偏好接口，未登录调用全量接口
  useEffect(() => {
    const fetchSeries = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = {
          page,
          limit,
          sort_by: sortBy,
          ...(genre !== '全部' ? { genre } : {}),
        };

        if (isAuthenticated && user) {
          const data = await contentApi.getPreferenceSeries(user.id, params);
          setSeries(data.results);
          setTotal(data.total);
          setIsFallback(data.is_fallback);
        } else {
          const data = await contentApi.getSeries(params);
          setSeries(data.results);
          setTotal(data.total);
          setIsFallback(false);
        }
      } catch (err) {
        console.error('获取剧集列表失败:', err);
        setError('获取剧集列表失败，请检查后端服务是否启动');
      } finally {
        setLoading(false);
      }
    };
    fetchSeries();
  }, [page, genre, sortBy, isAuthenticated, user]);

  // 获取待看清单 ID 列表
  useEffect(() => {
    if (!isAuthenticated || !user) return;
    contentApi.getWatchlist(user.id)
      .then(data => {
        const ids = data.watchlist.map((item: MediaItem) => item.id);
        setWatchlistIds(ids);
      })
      .catch(() => {});
  }, [isAuthenticated, user]);

  const totalPages = Math.ceil(total / limit);

  const handleAddToWatchlist = (id: number) => setWatchlistIds(prev => [...prev, id]);
  const handleRemoveFromWatchlist = (id: number) => setWatchlistIds(prev => prev.filter(wid => wid !== id));

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-secondary-100 rounded-full">
            <Tv className="w-8 h-8 text-secondary-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {isAuthenticated ? '我的剧集推荐' : '剧集库'}
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              共 {total} 部剧集
              {isAuthenticated && !isFallback && ' · 基于您的偏好'}
            </p>
          </div>
        </div>
        <Link to="/add-content">
          <Button variant="secondary">
            <Plus className="w-4 h-4 mr-2" />
            添加影视
          </Button>
        </Link>
      </div>

      {/* 偏好兜底提示横幅 */}
      {isAuthenticated && isFallback && (
        <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 text-blue-700">
          <Info className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">
            暂未找到您的偏好记录，正在展示全部剧集。
            您可以通过 <Link to="/add-content" className="underline font-medium">添加影视</Link> 来建立您的偏好库。
          </span>
        </div>
      )}

      {/* 筛选栏 */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-4 h-4 text-gray-500 flex-shrink-0" />
          <span className="text-sm text-gray-600 font-medium mr-1">类型：</span>
          {GENRES.map(g => (
            <button
              key={g}
              onClick={() => { setGenre(g); setPage(1); }}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                genre === g
                  ? 'bg-secondary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {g}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <SortAsc className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-600 font-medium mr-1">排序：</span>
          {SORT_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => { setSortBy(opt.value); setPage(1); }}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                sortBy === opt.value
                  ? 'bg-secondary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 flex items-center justify-between">
          <span>⚠️ {error}</span>
          <Button variant="outline" size="sm" onClick={() => setPage(p => p)}>重试</Button>
        </div>
      )}

      <MediaGrid
        items={series}
        loading={loading}
        emptyMessage={isAuthenticated ? '暂无偏好相关剧集' : '暂无剧集数据'}
        watchlistIds={watchlistIds}
        onAddToWatchlist={handleAddToWatchlist}
        onRemoveFromWatchlist={handleRemoveFromWatchlist}
      />

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-4">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
            <ChevronLeft className="w-4 h-4" />上一页
          </Button>
          <span className="text-gray-600 text-sm">第 {page} / {totalPages} 页</span>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
            下一页<ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      )}
    </div>
  );
};

export default Series;
