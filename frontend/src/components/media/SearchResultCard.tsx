import React from 'react';
import { Star, Calendar, Tag, CheckCircle } from 'lucide-react';
import { MediaItem } from '../../api/content';

interface SearchResultCardProps {
  item: MediaItem;
  isSelected: boolean;
  onClick: (item: MediaItem) => void;
}

const SearchResultCard: React.FC<SearchResultCardProps> = ({ item, isSelected, onClick }) => {
  return (
    <div
      onClick={() => onClick(item)}
      className={`flex gap-3 p-3 rounded-xl cursor-pointer transition-all border-2 ${
        isSelected
          ? 'border-primary-500 bg-primary-50'
          : 'border-transparent bg-white hover:bg-gray-50 hover:border-gray-200'
      }`}
    >
      {/* 封面图 */}
      <div className="flex-shrink-0 w-16 h-24 rounded-lg overflow-hidden bg-gray-200">
        {item.poster_path ? (
          <img
            src={item.poster_path}
            alt={item.title}
            className="w-full h-full object-cover"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <Tag className="w-6 h-6" />
          </div>
        )}
      </div>

      {/* 信息 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <h4 className="font-semibold text-gray-900 truncate">{item.title}</h4>
          {isSelected && <CheckCircle className="w-5 h-5 text-primary-500 flex-shrink-0" />}
        </div>

        <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
          {item.release_date && (
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {item.release_date}
            </span>
          )}
          <span className="px-1.5 py-0.5 bg-gray-100 rounded text-xs">
            {item.media_type === 'movie' ? '电影' : '剧集'}
          </span>
        </div>

        {item.genres && item.genres.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {item.genres.slice(0, 3).map((g, i) => (
              <span key={i} className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">
                {g}
              </span>
            ))}
          </div>
        )}

        {item.vote_average > 0 && (
          <div className="flex items-center gap-1 mt-1 text-sm text-yellow-600">
            <Star className="w-3 h-3 fill-yellow-400" />
            <span className="font-medium">{item.vote_average.toFixed(1)}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchResultCard;
