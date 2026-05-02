import React from 'react';
import { Link } from 'react-router-dom';
import { Film, Tv, List, Bot, Star, TrendingUp } from 'lucide-react';
import Button from '../components/common/Button';
import Card from '../components/common/Card';

const Home: React.FC = () => {
  const features = [
    {
      icon: <Bot className="w-8 h-8 text-primary-600" />,
      title: 'AI智能推荐',
      description: '基于自然语言理解的智能推荐系统，像聊天一样获取个性化推荐',
    },
    {
      icon: <Film className="w-8 h-8 text-primary-600" />,
      title: '海量影视库',
      description: '涵盖电影、剧集等多种类型，持续更新最新内容',
    },
    {
      icon: <List className="w-8 h-8 text-primary-600" />,
      title: '个性化清单',
      description: '创建和管理您的待看清单，随时标记观看进度',
    },
    {
      icon: <Star className="w-8 h-8 text-primary-600" />,
      title: '智能评分',
      description: '基于用户反馈和AI分析的精准评分系统',
    },
  ];

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center py-12">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
          智能影视推荐
          <span className="text-primary-600"> AI助手</span>
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          基于人工智能的影视推荐平台，通过自然语言对话为您提供个性化观影建议
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/agent">
            <Button variant="primary" size="lg">
              <Bot className="w-5 h-5 mr-2" />
              体验AI助手
            </Button>
          </Link>
          <Link to="/movies">
            <Button variant="outline" size="lg">
              <Film className="w-5 h-5 mr-2" />
              浏览电影
            </Button>
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section>
        <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
          核心功能
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <Card key={index} hover className="p-6">
              <div className="flex flex-col items-center text-center">
                <div className="mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Quick Access Section */}
      <section>
        <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
          快速访问
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link to="/movies">
            <Card hover className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-primary-100 rounded-lg">
                  <Film className="w-8 h-8 text-primary-600" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">电影库</h3>
                  <p className="text-gray-600">浏览海量电影资源</p>
                </div>
              </div>
            </Card>
          </Link>

          <Link to="/series">
            <Card hover className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-secondary-100 rounded-lg">
                  <Tv className="w-8 h-8 text-secondary-600" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">剧集库</h3>
                  <p className="text-gray-600">发现精彩电视剧集</p>
                </div>
              </div>
            </Card>
          </Link>

          <Link to="/agent">
            <Card hover className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-100 rounded-lg">
                  <TrendingUp className="w-8 h-8 text-green-600" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">AI助手</h3>
                  <p className="text-gray-600">智能对话推荐</p>
                </div>
              </div>
            </Card>
          </Link>
        </div>
      </section>

      {/* CTA Section */}
      <section className="text-center py-12">
        <Card className="bg-gradient-to-r from-primary-50 to-secondary-50 border-0">
          <div className="max-w-2xl mx-auto py-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              开始您的智能观影之旅
            </h2>
            <p className="text-gray-600 mb-8">
              注册账号，体验AI驱动的个性化推荐，发现您可能喜欢的影视作品
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register">
                <Button variant="primary" size="lg">
                  立即注册
                </Button>
              </Link>
              <Link to="/agent">
                <Button variant="outline" size="lg">
                  体验AI助手
                </Button>
              </Link>
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
};

export default Home;