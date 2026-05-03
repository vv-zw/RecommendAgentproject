import React, { useState, useEffect } from 'react';
import { Film, Filter, SortAsc, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import Card from '../components/common/Card';
import { CardContent } from '../components/common/Card';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { contentApi, MediaItem } from '../api/content';
import { useAuthStore } from '../store/authStore';

const GENRES = ['全部', '动作', '冒险', '科幻', '剧情', '喜剧', '恐怖', '动画', '纪录片', '爱情', '悬疑', '惊悚'];
const SORT_OPTIONS = [
  { label: '热度排序', value: 'popularity.desc' },
  { label: '评分排序', value: 'vote_average.desc' },
  { label: '最新上映', value: 'release_date.desc' },
];

const Movies: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const [movies, setMovies] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [genre, setGenre] = useState('全部');
  const [sortBy, setSortBy] = useState('popularity.desc');
  const limit = 20;

  useEffect(() => {
    const fetchMovies = async () => {
      setLoading(true);
      setError(null);
      try {
        if (isAuthenticated && user) {
          // 已登录：展示用户影片库
          const data = await contentApi.getLibraryMovies(user.id, { page, limit });
          setMovies(data.results);
          setTotal(data.total);
        } else {
          // 未登录：全量展示
          const params = {
            page, limit, sort_by: sortBy,
            ...(genre !== '全部' ? { genre } : {}),
          };
          const data = await contentApi.getMovies(params);
          setMovies(data.results);
          setTotal(data.total);
        }
      } catch (err) {
        console.error('获取电影列表失败:', err);
        setError('获取电影列表失败，请检查后端服务是否启动');
      } finally {
        setLoading(false);
      }
    };
    fetchMovies();
  }, [page, genre, sortBy, isAuthenticated, user]);

  const totalPages = Math.ceil(total / limit);

  // 已登录但影片库为空
  if (!loading && isAuthenticated && movies.length === 0 && !error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary-100 rounded-full">
              <Film className="w-8 h-8 text-primary-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">我的电影库</h1>
              <p className="text-gray-500 text-sm mt-1">您添加的电影收藏</p>
            </div>
          </div>
          <Link to="/add-content">
            <Button variant="primary"><Plus className="w-4 h-4 mr-2" />添加电影</Button>
          </Link>
        </div>
        <Card>
          <CardContent className="text-center py-16">
            <Film className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">您的电影库还是空的</h3>
            <p className="text-gray-600 mb-6">搜索并添加您喜欢的电影，建立专属影片库</p>
            <Link to="/add-content">
              <Button variant="primary"><Plus className="w-4 h-4 mr-2" />去添加电影</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary-100 rounded-full">
            <Film className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {isAuthenticated ? '我的电影库' : '电影库'}
            </h1>
            <p className="text-gray-500 text-sm mt-1">共 {total} 部电影</p>
          </div>
        </div>
        <Link to="/add-content">
          <Button variant="primary"><Plus className="w-4 h-4 mr-2" />添加影视</Button>
        </Link>
      </div>

      {/* 未登录时显示筛选栏 */}
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
                  genre === g ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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
                  sortBy === opt.value ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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
          {movies.map((movie) => (
            <div
              key={movie.id}
              onClick={() => navigate(`/movie/${movie.content_id || movie.id}`)}
              className="group bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-all duration-300 cursor-pointer"
            >
              <div className="relative h-64 overflow-hidden bg-gray-200">
                {movie.poster_path ? (
                  <img
                    src={movie.poster_path}
                    alt={movie.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Film className="w-12 h-12 text-gray-400" />
                  </div>
                )}
                {movie.vote_average > 0 && (
                  <div className="absolute top-3 right-3 bg-black/70 text-white px-2 py-1 rounded-full flex items-center gap-1 text-sm">
                    ⭐ {movie.vote_average.toFixed(1)}
                  </div>
                )}
              </div>
              <div className="p-4">
                <h3 className="font-semibold text-gray-900 truncate">{movie.title}</h3>
                <div className="flex flex-wrap gap-1 mt-2">
                  {movie.genres?.slice(0, 2).map((g, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 bg-primary-50 text-primary-600 rounded">{g}</span>
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

export default Movies;
