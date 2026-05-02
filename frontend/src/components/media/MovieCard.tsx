import React from 'react';
import { Star, Calendar, Tag } from 'lucide-react';
import { MediaItem } from '../../api/content';
import Button from '../common/Button';
import { useAuthStore } from '../../store/authStore';
import { contentApi } from '../../api/content';

interface MovieCardProps {
  movie: MediaItem;
  onAddToWatchlist?: () => void;
  onRemoveFromWatchlist?: () => void;
  isInWatchlist?: boolean;
  showActions?: boolean;
}

const MovieCard: React.FC<MovieCardProps> = ({
  movie,
  onAddToWatchlist,
  onRemoveFromWatchlist,
  isInWatchlist = false,
  showActions = true,
}) => {
  const { isAuthenticated } = useAuthStore();

  const handleWatchlistToggle = async () => {
    if (!isAuthenticated) {
      // 可以在这里添加登录提示
      return;
    }

    const userId = localStorage.getItem('user_id');
    if (!userId) return;

    try {
      if (isInWatchlist && onRemoveFromWatchlist) {
        await contentApi.removeFromWatchlist(parseInt(userId), movie.id);
        onRemoveFromWatchlist();
      } else if (!isInWatchlist && onAddToWatchlist) {
        await contentApi.addToWatchlist(parseInt(userId), movie.id);
        onAddToWatchlist();
      }
    } catch (error) {
      console.error('Failed to update watchlist:', error);
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return '未知';
    const date = new Date(dateString);
    return date.getFullYear();
  };

  return (
    <div className="group relative bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-all duration-300">
      {/* 海报 */}
      <div className="relative h-64 overflow-hidden">
        <img
          src={movie.poster_path || '/placeholder-poster.jpg'}
          alt={movie.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        
        {/* 评分标签 */}
        <div className="absolute top-3 right-3 bg-black/70 text-white px-2 py-1 rounded-full flex items-center gap-1">
          <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
          <span className="text-sm font-semibold">{movie.vote_average.toFixed(1)}</span>
        </div>
      </div>

      {/* 内容 */}
      <div className="p-4">
        <h3 className="text-lg font-semibold text-gray-900 truncate mb-2">
          {movie.title}
        </h3>
        
        <p className="text-sm text-gray-600 line-clamp-2 mb-3">
          {movie.overview || '暂无简介'}
        </p>
        
        {/* 元信息 */}
        <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            <span>{formatDate(movie.release_date)}</span>
          </div>
          
          <div className="flex items-center gap-1">
            <Tag className="w-4 h-4" />
            <span>{movie.genres?.[0] || '未知'}</span>
          </div>
        </div>

        {/* 操作按钮 */}
        {showActions && isAuthenticated && (
          <div className="flex gap-2">
            <Button
              variant={isInWatchlist ? 'secondary' : 'primary'}
              size="sm"
              fullWidth
              onClick={handleWatchlistToggle}
            >
              {isInWatchlist ? '已收藏' : '加入待看'}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              fullWidth
              onClick={() => window.open(`/movie/${movie.id}`, '_blank')}
            >
              查看详情
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MovieCard;