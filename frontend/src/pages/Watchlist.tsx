import React, { useState, useEffect, useCallback } from 'react';
import { Bookmark, Eye, Trash2, Star, Calendar, LogIn } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import Card from '../components/common/Card';
import { CardContent } from '../components/common/Card';
import Button from '../components/common/Button';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { contentApi, MediaItem } from '../api/content';
import { useAuthStore } from '../store/authStore';

const Watchlist: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const [watchlist, setWatchlist] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWatchlist = useCallback(async () => {
    if (!isAuthenticated || !user) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await contentApi.getWatchlist(user.id);
      setWatchlist(data.watchlist);
    } catch (err) {
      console.error('获取待看清单失败:', err);
      setError('待看清单加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, user]);

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  // 乐观更新移除：先从 UI 移除，失败时回滚
  const handleRemove = async (mediaId: number) => {
    if (!user) return;
    // 乐观更新
    setWatchlist(prev => prev.filter(item => item.id !== mediaId));
    try {
      await contentApi.removeFromWatchlist(user.id, mediaId);
    } catch (err) {
      console.error('移除失败，回滚:', err);
      // 回滚：重新加载列表
      fetchWatchlist();
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return '未知';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch {
      return dateString;
    }
  };

  // 未登录状态
  if (!isAuthenticated) {
    return (
      <div className="space-y-8">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary-100 rounded-full">
            <Bookmark className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">待看清单</h1>
            <p className="text-gray-600">管理您想看的影视内容</p>
          </div>
        </div>
        <Card>
          <CardContent className="text-center py-16">
            <LogIn className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">请先登录</h3>
            <p className="text-gray-600 mb-6">登录后即可查看和管理您的待看清单</p>
            <div className="flex gap-4 justify-center">
              <Link to="/login">
                <Button variant="primary">立即登录</Button>
              </Link>
              <Link to="/register">
                <Button variant="outline">注册账户</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* 页头 */}
      <div className="flex items-center gap-3">
        <div className="p-3 bg-primary-100 rounded-full">
          <Bookmark className="w-8 h-8 text-primary-600" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">待看清单</h1>
          <p className="text-gray-600">
            {loading ? '加载中...' : `共 ${watchlist.length} 部待看内容`}
          </p>
        </div>
      </div>

      {/* 加载状态 */}
      {loading && (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {/* 错误状态 */}
      {!loading && error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 flex items-center justify-between">
          <span>⚠️ {error}</span>
          <Button variant="outline" size="sm" onClick={fetchWatchlist}>重试</Button>
        </div>
      )}

      {/* 空状态 */}
      {!loading && !error && watchlist.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <Bookmark className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">待看清单为空</h3>
            <p className="text-gray-600 mb-6">您还没有添加任何影视内容到待看清单</p>
            <div className="flex gap-4 justify-center">
              <Link to="/movies">
                <Button variant="primary">浏览电影</Button>
              </Link>
              <Link to="/series">
                <Button variant="outline">浏览剧集</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 待看清单列表 */}
      {!loading && !error && watchlist.length > 0 && (
        <div className="space-y-4">
          {watchlist.map((item) => (
            <Card key={item.id} hover className="overflow-hidden">
              <div
                className="md:flex cursor-pointer"
                onClick={() => navigate(`/${item.media_type === 'movie' ? 'movie' : 'series'}/${item.id}`)}
              >
                {/* 海报 */}
                <div className="md:w-1/4 flex-shrink-0">
                  <div className="relative h-48 md:h-full min-h-[160px]">
                    {item.poster_path ? (
                      <img
                        src={item.poster_path}
                        alt={item.title}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="w-full h-full bg-gray-200 flex items-center justify-center">
                        <Bookmark className="w-12 h-12 text-gray-400" />
                      </div>
                    )}
                  </div>
                </div>

                {/* 内容 */}
                <div className="md:w-3/4 p-6">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium px-2 py-0.5 bg-gray-100 rounded text-gray-600">
                          {item.media_type === 'movie' ? '电影' : '剧集'}
                        </span>
                        {item.genres && item.genres.length > 0 && (
                          <span className="text-xs text-gray-500">{item.genres.slice(0, 2).join(' · ')}</span>
                        )}
                      </div>
                      <h3 className="text-xl font-semibold text-gray-900">{item.title}</h3>
                    </div>

                    {/* 评分 */}
                    {item.vote_average > 0 && (
                      <div className="flex items-center gap-1 text-yellow-600 flex-shrink-0 ml-4">
                        <Star className="w-4 h-4 fill-yellow-400" />
                        <span className="font-bold">{item.vote_average.toFixed(1)}</span>
                      </div>
                    )}
                  </div>

                  {/* 简介 */}
                  {item.overview && (
                    <p className="text-gray-600 mb-4 line-clamp-2 text-sm">{item.overview}</p>
                  )}

                  {/* 元信息 */}
                  <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                    {item.release_date && (
                      <div className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        <span>{item.release_date}</span>
                      </div>
                    )}
                    {item.added_at && (
                      <span>添加于 {formatDate(item.added_at)}</span>
                    )}
                  </div>

                  {/* 操作按钮 */}
                  <div className="flex gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => {
                        // 标记已看：添加到观看历史并从待看清单移除
                        if (user) {
                          contentApi.addToHistory(user.id, item.id).catch(() => {});
                          handleRemove(item.id);
                        }
                      }}
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      标记已看
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      onClick={() => handleRemove(item.id)}
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      移除
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default Watchlist;
