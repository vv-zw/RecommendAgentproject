import React from 'react';

const MediaDetailSkeleton: React.FC = () => {
  return (
    <div className="animate-pulse space-y-8">
      {/* 顶部横幅区域 */}
      <div className="h-64 bg-gray-200 rounded-2xl" />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* 左侧封面 */}
        <div className="md:col-span-1">
          <div className="aspect-[2/3] bg-gray-200 rounded-xl" />
        </div>

        {/* 右侧信息 */}
        <div className="md:col-span-2 space-y-4">
          {/* 标题 */}
          <div className="h-8 bg-gray-200 rounded w-3/4" />
          <div className="h-5 bg-gray-200 rounded w-1/2" />

          {/* 评分和标签 */}
          <div className="flex gap-3">
            <div className="h-8 w-20 bg-gray-200 rounded-full" />
            <div className="h-8 w-16 bg-gray-200 rounded-full" />
            <div className="h-8 w-16 bg-gray-200 rounded-full" />
          </div>

          {/* 元信息 */}
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded w-2/3" />
            <div className="h-4 bg-gray-200 rounded w-1/2" />
            <div className="h-4 bg-gray-200 rounded w-3/5" />
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-3 pt-2">
            <div className="h-10 w-32 bg-gray-200 rounded-lg" />
            <div className="h-10 w-32 bg-gray-200 rounded-lg" />
          </div>
        </div>
      </div>

      {/* 简介 */}
      <div className="space-y-2">
        <div className="h-5 bg-gray-200 rounded w-1/4" />
        <div className="h-4 bg-gray-200 rounded" />
        <div className="h-4 bg-gray-200 rounded" />
        <div className="h-4 bg-gray-200 rounded w-4/5" />
      </div>
    </div>
  );
};

export default MediaDetailSkeleton;
