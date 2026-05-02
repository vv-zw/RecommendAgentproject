import React from 'react';
import { Tv } from 'lucide-react';
import MediaGrid from '../components/media/MediaGrid';
import Button from '../components/common/Button';

const Series: React.FC = () => {
  // 这里应该是从API获取的数据
  const mockSeries = [
    {
      id: 1,
      title: '权力的游戏',
      overview: '在维斯特洛大陆上，七个王国为争夺铁王座而展开激烈的权力斗争。',
      poster_path: '/placeholder.jpg',
      backdrop_path: '/placeholder.jpg',
      release_date: '2011-04-17',
      vote_average: 8.9,
      vote_count: 20000,
      media_type: 'series',
      genres: ['奇幻', '剧情', '冒险'],
      popularity: 9.5,
    },
    {
      id: 2,
      title: '怪奇物语',
      overview: '一个小镇上的男孩神秘失踪，他的朋友、家人和当地警察在寻找答案时发现了超自然力量。',
      poster_path: '/placeholder.jpg',
      backdrop_path: '/placeholder.jpg',
      release_date: '2016-07-15',
      vote_average: 8.7,
      vote_count: 18000,
      media_type: 'series',
      genres: ['科幻', '恐怖', '剧情'],
      popularity: 8.8,
    },
    // 可以添加更多模拟数据
  ];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-secondary-100 rounded-full">
            <Tv className="w-8 h-8 text-secondary-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">剧集库</h1>
            <p className="text-gray-600">发现精彩电视剧集</p>
          </div>
        </div>
        
        <div className="flex gap-2">
          <Button variant="outline">筛选</Button>
          <Button variant="secondary">排序</Button>
        </div>
      </div>

      <MediaGrid
        items={mockSeries}
        emptyMessage="暂无剧集数据"
        type="series"
      />
    </div>
  );
};

export default Series;