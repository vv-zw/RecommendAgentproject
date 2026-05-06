import React from 'react';
import { Star, Calendar, Tag } from 'lucide-react';
import { MediaItem } from '../../api/content';
import { useNavigate } from 'react-router-dom';

interface RecommendationCardProps {
  item: MediaItem;
  reason?: string;
  rank?: number;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({ item, reason, rank }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    const path = item.media_type === 'movie' ? `/movie/${item.id}` : `/series/${item.id}`;
    navigate(path);
  };

  return (
    <div
      onClick={handleClick}
      className="flex gap-3 p-3 rounded-xl border border-gray-100 hover:border-primary-200 hover:bg-primary-50/30 cursor-pointer transition-all duration-200 group"
    >
      {/* 排名 */}
      {rank !== undefined && (
        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-700 text-xs font-bold flex items-center justify-center mt-0.5">
          {rank}
        </div>
      )}

      {/* 海报 */}
      <div className="flex-shrink-0 w-14 h-20 rounded-lg overflow-hidden bg-gray-100">
        {item.poster_path ? (
          <img
            src={item.poster_path}
            alt={item.title}
            className="w-full h-full object-cover"
            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs text-center px-1">
            暂无封面
          </div>
        )}
      </div>

      {/* 信息 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-1 mb-1">
          <h4 className="text-sm font-semibold text-gray-900 line-clamp-1 group-hover:text-primary-700 transition-colors">
            {item.title}
          </h4>
          <span className="flex-shrink-0 text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
            {item.media_type === 'movie' ? '电影' : '剧集'}
          </span>
        </div>

        {/* 评分 + 年份 */}
        <div className="flex items-center gap-3 text-xs text-gray-500 mb-1.5">
          {item.vote_average > 0 && (
            <span className="flex items-center gap-0.5 text-amber-600 font-medium">
              <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
              {item.vote_average.toFixed(1)}
            </span>
          )}
          {item.release_date && (
            <span className="flex items-center gap-0.5">
              <Calendar className="w-3 h-3" />
              {item.release_date}
            </span>
          )}
          {item.genres && item.genres.length > 0 && (
            <span className="flex items-center gap-0.5 truncate">
              <Tag className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">{item.genres.slice(0, 2).join(' · ')}</span>
            </span>
          )}
        </div>

        {/* 简介 */}
        {item.overview && (
          <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">
            {item.overview}
          </p>
        )}

        {/* 推荐理由 */}
        {reason && (
          <p className="text-xs text-primary-600 mt-1 line-clamp-1">
            💡 {reason}
          </p>
        )}
      </div>
    </div>
  );
};

export default RecommendationCard;
