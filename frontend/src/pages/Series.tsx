import React, { useState, useEffect } from 'react';
import { Tv, Filter, SortAsc, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import Card from '../components/common/Card';
import { CardContent } from '../components/common/Card';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { contentApi, MediaItem } from '../api/content';
import { useAuthStore } from '../store/authStore';

const GENRES = ['全部', '剧情', '喜剧', '爱情', '悬疑', '惊悚', '科幻', '奇幻', '动作', '历史', '犯罪', '动画'];
const SORT_OPTIONS = [
  { label: '热度排序', value: 'popularity.desc' },
  { label: '评分排序', value: 'vote_average.desc' },
  { label: '最新上映', value: 'release_date.desc' },
];

const Series: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const [series, setSeries] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [genre, setGenre] = useState('全部');
  const [sortBy, setSortBy] = useState('popularity.desc');
  const limit = 20;

  useEffect(() => {
    const fetchSeries = async () => {
      setLoading(true);
      setError(null);
      try {
        if (isAuthenticated && user) {
          const data = await contentApi.getLibrarySeries(user.id, { page, limit });
          setSeries(data.results);
          setTotal(data.total);
        } else {
          const params = {
            page, limit, sort_by: sortBy,
            ...(genre !== '全部' ? { genre } : {}),
          };
          const data = await contentApi.getSeries(params);
          setSeries(data.results);
          setTotal(data.total);
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

  const totalPages = Math.ceil(total / limit);

  if (!loading && isAuthenticated && series.length === 0 && !error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-secondary-100 rounded-full">
              <Tv className="w-8 h-8 text-secondary-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">我的剧集库</h1>
              <p className="text-gray-500 text-sm mt-1">您添加的剧集收藏</p>
            </div>
          </div>
          <Link to="/add-content">
            <Button variant="secondary"><Plus className="w-4 h-4 mr-2" />添加剧集</Button>
          </Link>
        </div>
        <Card>
          <CardContent className="text-center py-16">
            <Tv className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">您的剧集库还是空的</h3>
            <p className="text-gray-600 mb-6">搜索并添加您喜欢的剧集，建立专属剧集库</p>
            <Link to="/add-content">
              <Button variant="secondary"><Plus className="w-4 h-4 mr-2" />去添加剧集</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-secondary-100 rounded-full">
            <Tv className="w-8 h-8 text-secondary-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {isAuthenticated ? '我的剧集库' : '剧集库'}
            </h1>
            <p className="text-gray-500 text-sm mt-1">共 {total} 部剧集</p>
          </div>
        </div>
        <Link to="/add-content">
          <Button variant="secondary"><Plus className="w-4 h-4 mr-2" />添加影视</Button>
        </Link>
      </div>

      {!isAuthenticated && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="w-4 h-4 text-gray-500 flex-shrink-0" />
            <span className="text-sm text-gray-600 font-medium mr-1">类型：</span>
            {GENRES.map(g => (
              <button
                key={g}
                onClick={() => { setGenre(g); setPage(1); }}
                className={`px-3 py-1 rounded-full text-sm transition-colors ${
                  genre === g ? 'bg-secondary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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
                  sortBy === opt.value ? 'bg-secondary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 flex items-center justify-between">
          <span>⚠️ {error}</span>
          <Button variant="outline" size="sm" onClick={() => setPage(p => p)}>重试</Button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {series.map((item) => (
            <div
              key={item.id}
              onClick={() => navigate(`/series/${item.content_id || item.id}`)}
              className="group bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-all duration-300 cursor-pointer"
            >
              <div className="relative h-64 overflow-hidden bg-gray-200">
                {item.poster_path ? (
                  <img
                    src={item.poster_path}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Tv className="w-12 h-12 text-gray-400" />
                  </div>
                )}
                {item.vote_average > 0 && (
                  <div className="absolute top-3 right-3 bg-black/70 text-white px-2 py-1 rounded-full flex items-center gap-1 text-sm">
                    ⭐ {item.vote_average.toFixed(1)}
                  </div>
                )}
              </div>
              <div className="p-4">
                <h3 className="font-semibold text-gray-900 truncate">{item.title}</h3>
                <div className="flex flex-wrap gap-1 mt-2">
                  {item.genres?.slice(0, 2).map((g, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 bg-secondary-50 text-secondary-600 rounded">{g}</span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

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
