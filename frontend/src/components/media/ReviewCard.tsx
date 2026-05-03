import React from 'react';
import { Star, User } from 'lucide-react';
import { ReviewItem } from '../../api/content';

interface ReviewCardProps {
  review: ReviewItem;
}

const ReviewCard: React.FC<ReviewCardProps> = ({ review }) => {
  return (
    <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-primary-600" />
          </div>
          <span className="font-medium text-gray-900 text-sm">{review.author}</span>
        </div>
        <div className="flex items-center gap-2">
          {review.rating !== undefined && review.rating > 0 && (
            <div className="flex items-center gap-1 text-yellow-600 text-sm">
              <Star className="w-3 h-3 fill-yellow-400" />
              <span>{review.rating}</span>
            </div>
          )}
          {review.date && (
            <span className="text-xs text-gray-400">{review.date}</span>
          )}
        </div>
      </div>
      <p className="text-gray-700 text-sm line-clamp-4 leading-relaxed">{review.content}</p>
    </div>
  );
};

export default ReviewCard;
