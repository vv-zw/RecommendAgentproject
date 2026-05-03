import React from 'react';
import { Bookmark, Eye, Trash2 } from 'lucide-react';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import { CardContent } from '../components/common/Card';

const Watchlist: React.FC = () => {
  // 这里应该是从API获取的数据
  const mockWatchlist = [
    {
      id: 1,
      title: '流浪地球',
      overview: '太阳即将毁灭，人类在地球表面建造出巨大的推进器，寻找新的家园。',
      poster_path: '/placeholder.jpg',
      added_at: '2024-01-15',
      media_type: 'movie',
      vote_average: 7.9,
    },
    {
      id: 2,
      title: '权力的游戏',
      overview: '在维斯特洛大陆上，七个王国为争夺铁王座而展开激烈的权力斗争。',
      poster_path: '/placeholder.jpg',
      added_at: '2024-01-10',
      media_type: 'series',
      vote_average: 8.9,
    },
    {
      id: 3,
      title: '怪奇物语',
      overview: '一个小镇上的男孩神秘失踪，他的朋友、家人和当地警察在寻找答案时发现了超自然力量。',
      poster_path: '/placeholder.jpg',
      added_at: '2024-01-05',
      media_type: 'series',
      vote_average: 8.7,
    },
  ];

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

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

      {mockWatchlist.length > 0 ? (
        <div className="space-y-4">
          {mockWatchlist.map((item) => (
            <Card key={item.id} hover className="overflow-hidden">
              <div className="md:flex">
                {/* 海报 */}
                <div className="md:w-1/4">
                  <img
                    src={item.poster_path || '/placeholder.jpg'}
                    alt={item.title}
                    className="w-full h-48 md:h-full object-cover"
                  />
                </div>

                {/* 内容 */}
                <div className="md:w-3/4 p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium px-2 py-1 bg-gray-100 rounded">
                          {item.media_type === 'movie' ? '电影' : '剧集'}
                        </span>
                        <span className="text-sm text-gray-500">
                          添加于 {formatDate(item.added_at)}
                        </span>
                      </div>
                      <h3 className="text-xl font-semibold text-gray-900">
                        {item.title}
                      </h3>
                    </div>
                    
                    <div className="flex items-center gap-1 text-yellow-600">
                      <span className="text-lg font-bold">{item.vote_average.toFixed(1)}</span>
                      <span className="text-sm">/10</span>
                    </div>
                  </div>

                  <p className="text-gray-600 mb-4 line-clamp-2">
                    {item.overview}
                  </p>

                  <div className="flex gap-2">
                    <Button variant="primary" size="sm">
                      <Eye className="w-4 h-4 mr-1" />
                      标记已看
                    </Button>
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                    <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700">
                      <Trash2 className="w-4 h-4 mr-1" />
                      移除
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <Bookmark className="w-16 h-16 mx-auto" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              待看清单为空
            </h3>
            <p className="text-gray-600 mb-6">
              您还没有添加任何影视内容到待看清单
            </p>
            <div className="flex gap-4 justify-center">
              <Button variant="primary" onClick={() => window.location.href = '/movies'}>
                浏览电影
              </Button>
              <Button variant="outline" onClick={() => window.location.href = '/series'}>
                浏览剧集
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Watchlist;