import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Star, Calendar, MapPin, Tv, User,
  Bookmark, BookmarkCheck, Plus, CheckCircle, ArrowLeft, Tag, Hash
} from 'lucide-react';
import { contentApi, ContentDetail } from '../api/content';
import { useAuthStore } from '../store/authStore';
import MediaDetailSkeleton from '../components/media/MediaDetailSkeleton';
import ReviewCard from '../components/media/ReviewCard';
import Button from '../components/common/Button';

const SeriesDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();

  const [detail, setDetail] = useState<ContentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inWatchlist, setInWatchlist] = useState(false);
  const [inLibrary, setInLibrary] = useState(false);
  const [actionLoading, setActionLoading] = useState<'watchlist' | 'library' | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    if (!id) return;
    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await contentApi.getContentDetail(parseInt(id));
        setDetail(data);
      } catch (err: unknown) {
        const e = err as { response?: { status?: number } };
        if (e.response?.status === 404) {
          setError('剧集不存在');
        } else {
          setError('加载失败，请稍后重试');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [id]);

  useEffect(() => {
    if (!isAuthenticated || !user || !id) return;
    contentApi.getWatchlist(user.id).then(data => {
      setInWatchlist(data.watchlist.some((item) => String(item.id) === id));
    }).catch(() => {});
    contentApi.getUserPreferences(user.id).then(data => {
      setInLibrary(data.preferences.some(p => String(p.content_id) === id));
    }).catch(() => {});
  }, [isAuthenticated, user, id]);

  const handleAddToWatchlist = async () => {
    if (!isAuthenticated || !user) { showToast('请先登录'); return; }
    setActionLoading('watchlist');
    try {
      await contentApi.addToWatchlist(user.id, parseInt(id!));
      setInWatchlist(true);
      showToast('已加入待看清单');
    } catch {
      showToast('操作失败，请重试');
    } finally {
      setActionLoading(null);
    }
  };

  const handleAddToLibrary = async () => {
    if (!isAuthenticated || !user || !detail) { showToast('请先登录'); return; }
    setActionLoading('library');
    try {
      const result = await contentApi.addToLibrary(user.id, {
        content_id: String(detail.id),
        content_type: 'series',
        title: detail.title,
        genres: detail.genres?.join('/') || '',
        rating: detail.vote_average,
        year: detail.release_date ? parseInt(detail.release_date) : undefined,
        director: detail.director,
        actors: detail.actors,
        cover_url: detail.poster_path,
      });
      setInLibrary(true);
      showToast(result.message);
    } catch {
      showToast('操作失败，请重试');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return <div className="max-w-5xl mx-auto"><MediaDetailSkeleton /></div>;
  }

  if (error || !detail) {
    return (
      <div className="max-w-5xl mx-auto text-center py-20">
        <Tv className="w-16 h-16 mx-auto text-gray-300 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">{error || '剧集不存在'}</h2>
        <p className="text-gray-500 mb-6">无法找到该剧集的信息</p>
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-4 h-4 mr-2" />返回上一页
        </Button>
      </div>
    );
  }

  const reviews = detail.raw_source?.reviews || [];
  const cast = detail.raw_source?.cast || [];

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {toast && (
        <div className="fixed top-20 right-6 z-50 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg text-sm animate-fade-in">
          {toast}
        </div>
      )}

      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-gray-500 hover:text-gray-900 transition-colors">
        <ArrowLeft className="w-4 h-4" />返回
      </button>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* 封面 */}
        <div className="md:col-span-1">
          <div className="aspect-[2/3] rounded-2xl overflow-hidden bg-gray-200 shadow-lg">
            {detail.poster_path ? (
              <img
                src={detail.poster_path}
                alt={detail.title}
                className="w-full h-full object-cover"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Tv className="w-16 h-16 text-gray-400" />
              </div>
            )}
          </div>
        </div>

        {/* 信息 */}
        <div className="md:col-span-2 space-y-5">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 bg-secondary-100 text-secondary-700 rounded text-xs font-medium">剧集</span>
            </div>
            <h1 className="text-3xl font-bold text-gray-900">{detail.title}</h1>
            {detail.original_title && <p className="text-gray-500 mt-1">{detail.original_title}</p>}
          </div>

          {detail.vote_average > 0 && (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 bg-yellow-50 border border-yellow-200 px-3 py-1.5 rounded-full">
                <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                <span className="font-bold text-yellow-700 text-lg">{detail.vote_average.toFixed(1)}</span>
              </div>
              <span className="text-gray-500 text-sm">豆瓣评分</span>
            </div>
          )}

          {detail.genres && detail.genres.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {detail.genres.map((g, i) => (
                <span key={i} className="px-3 py-1 bg-secondary-50 text-secondary-700 rounded-full text-sm font-medium">{g}</span>
              ))}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 text-sm">
            {detail.release_date && (
              <div className="flex items-center gap-2 text-gray-600">
                <Calendar className="w-4 h-4 text-gray-400" />
                <span>首播年份：{detail.release_date}</span>
              </div>
            )}
            {detail.region && (
              <div className="flex items-center gap-2 text-gray-600">
                <MapPin className="w-4 h-4 text-gray-400" />
                <span>地区：{detail.region}</span>
              </div>
            )}
            {detail.language && (
              <div className="flex items-center gap-2 text-gray-600">
                <Tag className="w-4 h-4 text-gray-400" />
                <span>语言：{detail.language}</span>
              </div>
            )}
            {detail.episodes && (
              <div className="flex items-center gap-2 text-gray-600">
                <Hash className="w-4 h-4 text-gray-400" />
                <span>集数：{detail.episodes}</span>
              </div>
            )}
            {detail.director && (
              <div className="flex items-center gap-2 text-gray-600">
                <Tv className="w-4 h-4 text-gray-400" />
                <span>导演：{detail.director}</span>
              </div>
            )}
          </div>

          {detail.actors && (
            <div>
              <div className="flex items-center gap-2 text-gray-700 font-medium mb-2">
                <User className="w-4 h-4" />主演
              </div>
              <div className="flex flex-wrap gap-2">
                {detail.actors.split('/').filter(Boolean).map((actor, i) => (
                  <span key={i} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm">{actor.trim()}</span>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button
              variant={inWatchlist ? 'outline' : 'primary'}
              onClick={handleAddToWatchlist}
              isLoading={actionLoading === 'watchlist'}
              disabled={!!actionLoading}
            >
              {inWatchlist ? <><BookmarkCheck className="w-4 h-4 mr-2" />已加入待看</> : <><Bookmark className="w-4 h-4 mr-2" />加入待看清单</>}
            </Button>
            <Button
              variant={inLibrary ? 'outline' : 'secondary'}
              onClick={handleAddToLibrary}
              isLoading={actionLoading === 'library'}
              disabled={!!actionLoading}
            >
              {inLibrary ? <><CheckCircle className="w-4 h-4 mr-2" />已在影片库</> : <><Plus className="w-4 h-4 mr-2" />加入我的影片库</>}
            </Button>
          </div>
        </div>
      </div>

      {detail.overview && (
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-3">剧情简介</h2>
          <p className="text-gray-700 leading-relaxed">{detail.overview}</p>
        </div>
      )}

      {cast.length > 0 && (
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-4">演员表</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {cast.map((member, i) => (
              <div key={i} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                <div className="w-8 h-8 bg-secondary-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-secondary-600" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{member.name}</p>
                  {member.role && <p className="text-xs text-gray-500 truncate">{member.role}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {reviews.length > 0 && (
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-4">热门影评</h2>
          <div className="space-y-3">
            {reviews.slice(0, 5).map((review, i) => (
              <ReviewCard key={i} review={review} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SeriesDetail;
