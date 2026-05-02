import React from 'react';
import { Film } from 'lucide-react';
import MediaGrid from '../components/media/MediaGrid';
import Button from '../components/common/Button';
import { MediaItem } from '../api/content';

const Movies: React.FC = () => {
  // 这里应该是从API获取的数据
  const mockMovies: MediaItem[] = [
    {
      id: 1,
      title: '流浪地球',
      overview: '太阳即将毁灭，人类在地球表面建造出巨大的推进器，寻找新的家园。',
      poster_path: '/placeholder.jpg',
      backdrop_path: '/placeholder.jpg',
      release_date: '2019-02-05',
      vote_average: 7.9,
      vote_count: 15000,
      media_type: 'movie',
      genres: ['科幻', '冒险', '灾难'],
      popularity: 8.5,
    },
    {
      id: 2,
      title: '复仇者联盟4：终局之战',
      overview: '复仇者联盟在灭霸毁灭宇宙后，穿越时空收集无限宝石，试图恢复宇宙秩序。',
      poster_path: '/placeholder.jpg',
      backdrop_path: '/placeholder.jpg',
      release_date: '2019-04-24',
      vote_average: 8.4,
      vote_count: 25000,
      media_type: 'movie',
      genres: ['动作', '冒险', '科幻'],
      popularity: 9.2,
    },
    // 可以添加更多模拟数据
  ];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary-100 rounded-full">
            <Film className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">电影库</h1>
            <p className="text-gray-600">浏览海量电影资源</p>
          </div>
        </div>
        
        <div className="flex gap-2">
          <Button variant="outline">筛选</Button>
          <Button variant="primary">排序</Button>
        </div>
      </div>

      <MediaGrid
        items={mockMovies}
        emptyMessage="暂无电影数据"
      />
    </div>
  );
};

export default Movies;