import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Search, Film, Tv, CheckCircle, X, LogIn, PlusCircle, AlertCircle } from 'lucide-react';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import SearchResultCard from '../components/media/SearchResultCard';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { contentApi, MediaItem } from '../api/content';
import { useAuthStore } from '../store/authStore';

const AddContent: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();

  const [query, setQuery] = useState('');
  const [mediaType, setMediaType] = useState<'movie' | 'series'>('movie');
  const [searchResults, setSearchResults] = useState<MediaItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);
  const [adding, setAdding] = useState(false);
  const [addStatus, setAddStatus] = useState<'idle' | 'success' | 'exists' | 'error'>('idle');
  const [addMessage, setAddMessage] = useState('');

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 防抖搜索
  const doSearch = useCallback(async (q: string, type: string) => {
    if (!q.trim()) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    setSearchError(null);
    try {
      const data = await contentApi.searchMedia(q, { media_type: type, limit: 10 });
      setSearchResults(data.results);
    } catch {
      setSearchError('搜索失败，请稍后重试');
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      doSearch(query, mediaType);
    }, 300);
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [query, mediaType, doSearch]);

  // 切换类型时清空选中
  const handleTypeChange = (type: 'movie' | 'series') => {
    setMediaType(type);
    setSelectedItem(null);
    setAddStatus('idle');
  };

  const handleSelectItem = (item: MediaItem) => {
    setSelectedItem(item);
    setAddStatus('idle');
  };

  const handleClearSelection = () => {
    setSelectedItem(null);
    setAddStatus('idle');
  };

  const handleConfirmAdd = async () => {
    if (!selectedItem || !user) return;
    setAdding(true);
    setAddStatus('idle');
    try {
      const result = await contentApi.addToLibrary(user.id, {
        content_id: String(selectedItem.id),
        content_type: mediaType,
        title: selectedItem.title,
        genres: selectedItem.genres?.join('/') || '',
        rating: selectedItem.vote_average,
        year: selectedItem.release_date ? parseInt(selectedItem.release_date) : undefined,
        director: selectedItem.director,
        actors: selectedItem.actors,
        cover_url: selectedItem.poster_path,
      });
      if (result.message.includes('已在')) {
        setAddStatus('exists');
      } else {
        setAddStatus('success');
      }
      setAddMessage(result.message);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } } };
      setAddStatus('error');
      setAddMessage(e.response?.data?.error || '添加失败，请稍后重试');
    } finally {
      setAdding(false);
    }
  };

  // 未登录状态
  if (!isAuthenticated) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <Card className="p-8 text-center">
          <LogIn className="w-16 h-16 mx-auto text-gray-300 mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">请先登录</h2>
          <p className="text-gray-600 mb-6">登录后即可搜索并添加影视到您的个人影片库</p>
          <div className="flex gap-4 justify-center">
            <Link to="/login"><Button variant="primary">立即登录</Button></Link>
            <Link to="/register"><Button variant="outline">注册账户</Button></Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* 页头 */}
      <div className="flex items-center gap-3">
        <div className="p-3 bg-green-100 rounded-full">
          <PlusCircle className="w-8 h-8 text-green-600" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">添加影视</h1>
          <p className="text-gray-500 text-sm mt-1">搜索并添加影片到您的个人影片库</p>
        </div>
      </div>

      {/* 搜索区 */}
      <Card className="p-6 space-y-4">
        {/* 类型选择 */}
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => handleTypeChange('movie')}
            className={`flex items-center justify-center gap-2 p-3 rounded-xl border-2 transition-all ${
              mediaType === 'movie'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-200 hover:border-gray-300 text-gray-600'
            }`}
          >
            <Film className="w-5 h-5" />
            <span className="font-medium">电影</span>
          </button>
          <button
            type="button"
            onClick={() => handleTypeChange('series')}
            className={`flex items-center justify-center gap-2 p-3 rounded-xl border-2 transition-all ${
              mediaType === 'series'
                ? 'border-secondary-500 bg-secondary-50 text-secondary-700'
                : 'border-gray-200 hover:border-gray-300 text-gray-600'
            }`}
          >
            <Tv className="w-5 h-5" />
            <span className="font-medium">剧集</span>
          </button>
        </div>

        {/* 搜索框 */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`搜索${mediaType === 'movie' ? '电影' : '剧集'}名称...`}
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          {query && (
            <button
              onClick={() => { setQuery(''); setSearchResults([]); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* 搜索状态 */}
        {searching && (
          <div className="flex justify-center py-4">
            <LoadingSpinner size="sm" />
          </div>
        )}

        {searchError && (
          <p className="text-sm text-red-600 flex items-center gap-1">
            <AlertCircle className="w-4 h-4" />{searchError}
          </p>
        )}

        {/* 搜索结果 */}
        {!searching && searchResults.length > 0 && (
          <div className="space-y-2 max-h-80 overflow-y-auto">
            <p className="text-sm text-gray-500">找到 {searchResults.length} 个结果，点击选择：</p>
            {searchResults.map((item) => (
              <SearchResultCard
                key={item.id}
                item={item}
                isSelected={selectedItem?.id === item.id}
                onClick={handleSelectItem}
              />
            ))}
          </div>
        )}

        {!searching && query && searchResults.length === 0 && !searchError && (
          <div className="text-center py-6 text-gray-500">
            <Search className="w-10 h-10 mx-auto text-gray-300 mb-2" />
            <p>未找到匹配的{mediaType === 'movie' ? '电影' : '剧集'}</p>
            <p className="text-sm mt-1">请尝试其他关键词</p>
          </div>
        )}
      </Card>

      {/* 预览面板 */}
      {selectedItem && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">已选择影片</h3>
            <button onClick={handleClearSelection} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex gap-4">
            {/* 封面 */}
            <div className="flex-shrink-0 w-24 h-36 rounded-lg overflow-hidden bg-gray-200">
              {selectedItem.poster_path ? (
                <img
                  src={selectedItem.poster_path}
                  alt={selectedItem.title}
                  className="w-full h-full object-cover"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400">
                  <Film className="w-8 h-8" />
                </div>
              )}
            </div>

            {/* 信息 */}
            <div className="flex-1 space-y-2">
              <h4 className="text-xl font-bold text-gray-900">{selectedItem.title}</h4>
              <div className="flex flex-wrap gap-2 text-sm text-gray-600">
                {selectedItem.release_date && <span>📅 {selectedItem.release_date}</span>}
                {selectedItem.vote_average > 0 && <span>⭐ {selectedItem.vote_average.toFixed(1)}</span>}
                <span className="px-2 py-0.5 bg-gray-100 rounded">
                  {selectedItem.media_type === 'movie' ? '电影' : '剧集'}
                </span>
              </div>
              {selectedItem.genres && selectedItem.genres.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedItem.genres.map((g, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded">{g}</span>
                  ))}
                </div>
              )}
              {selectedItem.overview && (
                <p className="text-sm text-gray-600 line-clamp-2">{selectedItem.overview}</p>
              )}
            </div>
          </div>

          {/* 添加状态提示 */}
          {addStatus === 'success' && (
            <div className="mt-4 flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg p-3 text-green-700">
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
              <span>{addMessage}</span>
              <button
                className="ml-auto text-sm underline"
                onClick={() => navigate(mediaType === 'movie' ? '/movies' : '/series')}
              >
                查看影片库
              </button>
            </div>
          )}
          {addStatus === 'exists' && (
            <div className="mt-4 flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg p-3 text-blue-700">
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
              <span>{addMessage}</span>
            </div>
          )}
          {addStatus === 'error' && (
            <div className="mt-4 flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg p-3 text-red-700">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{addMessage}</span>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex gap-3 mt-4">
            <Button
              variant="primary"
              fullWidth
              onClick={handleConfirmAdd}
              isLoading={adding}
              disabled={adding || addStatus === 'success'}
            >
              <PlusCircle className="w-4 h-4 mr-2" />
              {addStatus === 'success' ? '已添加' : '确认添加到影片库'}
            </Button>
            <Button variant="outline" onClick={handleClearSelection} disabled={adding}>
              取消
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};

export default AddContent;
