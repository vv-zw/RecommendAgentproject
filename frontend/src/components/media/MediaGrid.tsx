import React from 'react';
import { MediaItem } from '../../api/content';
import MovieCard from './MovieCard';

interface MediaGridProps {
  items: MediaItem[];
  loading?: boolean;
  emptyMessage?: string;
  onAddToWatchlist?: (itemId: number) => void;
  onRemoveFromWatchlist?: (itemId: number) => void;
  watchlistIds?: number[];
}

const MediaGrid: React.FC<MediaGridProps> = ({
  items,
  loading = false,
  emptyMessage = '暂无内容',
  onAddToWatchlist,
  onRemoveFromWatchlist,
  watchlistIds = [],
}) => {
  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 mb-4">
          <svg
            className="w-16 h-16 mx-auto"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1}
              d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <p className="text-gray-600 text-lg">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {items.map((item) => (
        <MovieCard
          key={item.id}
          movie={item}
          isInWatchlist={watchlistIds.includes(item.id)}
          onAddToWatchlist={() => onAddToWatchlist?.(item.id)}
          onRemoveFromWatchlist={() => onRemoveFromWatchlist?.(item.id)}
        />
      ))}
    </div>
  );
};

export default MediaGrid;