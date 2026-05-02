import React from 'react';
import { Star, Calendar, Tag, ExternalLink } from 'lucide-react';
import { MediaItem } from '../../api/content';
import Button from '../common/Button';

interface RecommendationCardProps {
  item: MediaItem;
  reason?: string;
  rank?: number;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({
  item,
  reason,
  rank,
}) => {
  const formatDate = (dateString: string) => {
    if (!dateString) return '未知';
    const date = new Date(dateString);
    return date.getFullYear();
  };

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200 hover:shadow-lg transition-shadow duration-300">
      {/* 排名徽章 */}
      {rank !== undefined && (
        <div className="absolute top-3 left-3 z-10">
          <div className="bg-primary-600 text-white w-8 h-8 rounded-full flex items-center justify-center font-bold">
            {rank}
          </div>
        </div>
      )}

      <div className="md:flex">
        {/* 海报 */}
        <div className="md:w-1/3">
          <div className="relative h-48 md:h-full">
            <img
              src={item.poster_path || '/placeholder-poster.jpg'}
              alt={item.title}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
            
            {/* 评分 */}
            <div className="absolute bottom-3 right-3 bg-black/70 text-white px-2 py-1 rounded-full flex items-center gap-1">
              <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
              <span className="text-sm font-semibold">{item.vote_average.toFixed(1)}</span>
            </div>
          </div>
        </div>

        {/* 内容 */}
        <div className="md:w-2/3 p-4">
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-xl font-bold text-gray-900">{item.title}</h3>
            <span className="text-sm text-gray-500">
              {item.media_type === 'movie' ? '电影' : '剧集'}
            </span>
          </div>

          {/* 元信息 */}
          <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
            <div className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              <span>{formatDate(item.release_date)}</span>
            </div>
            
            <div className="flex items-center gap-1">
              <Tag className="w-4 h-4" />
              <span>{item.genres?.join(' · ') || '未知'}</span>
            </div>
          </div>

          {/* 简介 */}
          <p className="text-gray-700 mb-4 line-clamp-3">
            {item.overview || '暂无简介'}
          </p>

          {/* 推荐理由 */}
          {reason && (
            <div className="mb-4">
              <div className="text-sm font-semibold text-gray-900 mb-1">推荐理由：</div>
              <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                {reason}
              </p>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() => window.open(`/${item.media_type}/${item.id}`, '_blank')}
            >
              查看详情
              <ExternalLink className="w-3 h-3 ml-1" />
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                // 这里可以添加添加到待看清单的逻辑
              }}
            >
              加入待看
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecommendationCard;