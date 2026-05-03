import React, { useState, useEffect } from 'react';
import { Film, Filter, SortAsc, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import MediaGrid from '../components/media/MediaGrid';
import Button from '../components/common/Button';
import { contentApi, MediaItem } from '../api/content';
import { useAuthStore } from '../store/authStore';

const GENRES = ['全部', '动作', '冒险', '科幻', '剧情', '喜剧', '恐怖', '动画', '纪录片', '爱情', '悬疑', '惊悚'];
const SORT_OPTIONS = [
  { label: '热度排序', value: 'popularity.desc' },
  { label: '评分排序', value: 'vote_average.desc' },
  { label: '最新上映', value: 'release_date.desc' },
];

const Movies: React.FC = () => {
  const { isAuthenticated, user } = useAuthStore();
  const [movies, setMovies] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [genre, setGenre] = useState('全部');
  const [sortBy, setSortBy] = useState('popularity.desc');
  const [watchlistIds, setWatchlistIds] = useState<number[]>([]);
  const limit = 20;

  // 获取电影列表
  useEffect(() => {
    const fetchMovies = async () => {
      setLoading(true);
      setError(null);
      try {
        const params: Record<string, unknown> = { page, limit, sort_by: sortBy };
        if (genre !== '全部') params.genre = genre;

        const data = await contentApi.getMovies(params as Parameters<typeof contentApi.getMovies>[0]);
        setMovies(data.results);
        setTotal(data.total);
      } catch (err) {
        console.error('获取电影列表失败:', err);
        setError('获取电影列表失败，请检查后端服务是否启动');
      } finally {
        setLoading(false);
      }
    };
    fetchMovies();
  }, [page, genre, sortBy]);

  // 获取待看清单
  useEffect(() => {
    if (!isAuthenticated || !user) return;
    contentApi.getWatchlist(user.id)
      .then(data => {
        const ids = data.watchlist.map((item: { media_id: number }) => item.media_id);
        setWatchlistIds(ids);
      })
      .catch(() => {});
  }, [isAuthenticated, user]);

  const totalPages = Math.ceil(total / limit);

  const handleAddToWatchlist = (id: number) => {
    setWatchlistIds(prev => [...prev, id]);
  };
  const handleRemoveFromWatchlist = (id: number) => {
    setWatchlistIds(prev => prev.filter(wid => wid !== id));
  };

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary-100 rounded-full">
            <Film className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">电影库</h1>
            <p className="text-gray-500 text-sm mt-1">共 {total} 部电影</p>
          </div>
        </div>
        <Link to="/add-content">
          <Button variant="primary">
            <Plus className="w-4 h-4 mr-2" />
            添加影视
          </Button>
        </Link>
      </div>

      {/* 筛选栏 */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
        {/* 类型筛选 */}
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-4 h-4 text-gray-500 flex-shrink-0" />
          <span className="text-sm text-gray-600 font-medium mr-1">类型：</span>
          {GENRES.map(g => (
            <button
              key={g}
              onClick={() => { setGenre(g); setPage(1); }}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                genre === g
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {g}
            </button>
          ))}
        </div>

        {/* 排序 */}
        <div className="flex items-center gap-2">
          <SortAsc className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-600 font-medium mr-1">排序：</span>
          {SORT_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => { setSortBy(opt.value); setPage(1); }}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                sortBy === opt.value
                  ? 'bg-primary-600 text-white'
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
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
          ⚠️ {error}
        </div>
      )}

      {/* 电影网格 */}
      <MediaGrid
        items={movies}
        loading={loading}
        emptyMessage="暂无电影数据"
        watchlistIds={watchlistIds}
        onAddToWatchlist={handleAddToWatchlist}
        onRemoveFromWatchlist={handleRemoveFromWatchlist}
      />

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
          >
            <ChevronLeft className="w-4 h-4" />
            上一页
          </Button>
          <span className="text-gray-600 text-sm">
            第 {page} / {totalPages} 页
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
          >
            下一页
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      )}
    </div>
  );
};

export default Movies;
