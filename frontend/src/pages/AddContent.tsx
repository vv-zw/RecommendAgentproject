import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusCircle, Film, Tv, Star, CheckCircle, AlertCircle, X } from 'lucide-react';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import { contentApi } from '../api/content';

const GENRE_OPTIONS = [
  '动作', '冒险', '科幻', '剧情', '喜剧', '恐怖', '动画',
  '纪录片', '爱情', '悬疑', '惊悚', '奇幻', '历史', '犯罪',
  '战争', '音乐', '传记', '家庭', '西部', '运动',
];

interface FormData {
  title: string;
  media_type: 'movie' | 'series';
  overview: string;
  release_date: string;
  vote_average: string;
  vote_count: string;
  popularity: string;
  poster_path: string;
  backdrop_path: string;
  genres: string[];
}

const initialForm: FormData = {
  title: '',
  media_type: 'movie',
  overview: '',
  release_date: '',
  vote_average: '',
  vote_count: '',
  popularity: '',
  poster_path: '',
  backdrop_path: '',
  genres: [],
};

const AddContent: React.FC = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormData>(initialForm);
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [submitMessage, setSubmitMessage] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
    if (errors[name as keyof FormData]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const toggleGenre = (genre: string) => {
    setForm(prev => ({
      ...prev,
      genres: prev.genres.includes(genre)
        ? prev.genres.filter(g => g !== genre)
        : [...prev.genres, genre],
    }));
  };

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof FormData, string>> = {};

    if (!form.title.trim()) newErrors.title = '请输入标题';
    if (form.vote_average && (isNaN(Number(form.vote_average)) || Number(form.vote_average) < 0 || Number(form.vote_average) > 10)) {
      newErrors.vote_average = '评分范围为 0 ~ 10';
    }
    if (form.vote_count && isNaN(Number(form.vote_count))) {
      newErrors.vote_count = '请输入有效数字';
    }
    if (form.popularity && isNaN(Number(form.popularity))) {
      newErrors.popularity = '请输入有效数字';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);
    setSubmitStatus('idle');

    try {
      const payload = {
        title: form.title.trim(),
        media_type: form.media_type,
        overview: form.overview.trim(),
        release_date: form.release_date || undefined,
        vote_average: form.vote_average ? parseFloat(form.vote_average) : 0,
        vote_count: form.vote_count ? parseInt(form.vote_count) : 0,
        popularity: form.popularity ? parseFloat(form.popularity) : 0,
        poster_path: form.poster_path.trim(),
        backdrop_path: form.backdrop_path.trim(),
        genres: form.genres,
      };

      await contentApi.addContent(payload);
      setSubmitStatus('success');
      setSubmitMessage(`《${form.title}》已成功添加到数据库！`);
      setForm(initialForm);

      // 3秒后跳转
      setTimeout(() => {
        navigate(form.media_type === 'movie' ? '/movies' : '/series');
      }, 2500);
    } catch (err: unknown) {
      console.error('添加失败:', err);
      const message = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || '添加失败，请稍后重试';
      setSubmitStatus('error');
      setSubmitMessage(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setForm(initialForm);
    setErrors({});
    setSubmitStatus('idle');
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* 页头 */}
      <div className="flex items-center gap-3">
        <div className="p-3 bg-green-100 rounded-full">
          <PlusCircle className="w-8 h-8 text-green-600" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">添加影视内容</h1>
          <p className="text-gray-500 text-sm mt-1">手动向数据库添加电影或剧集</p>
        </div>
      </div>

      {/* 成功/失败提示 */}
      {submitStatus === 'success' && (
        <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl p-4 text-green-700">
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          <span>{submitMessage}</span>
          <span className="ml-auto text-sm text-green-500">即将跳转...</span>
        </div>
      )}
      {submitStatus === 'error' && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{submitMessage}</span>
          <button onClick={() => setSubmitStatus('idle')} className="ml-auto">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <Card className="p-6 space-y-6">
          {/* 类型选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">内容类型 *</label>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setForm(prev => ({ ...prev, media_type: 'movie' }))}
                className={`flex items-center justify-center gap-3 p-4 rounded-xl border-2 transition-all ${
                  form.media_type === 'movie'
                    ? 'border-primary-600 bg-primary-50 text-primary-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <Film className="w-6 h-6" />
                <span className="font-medium text-lg">电影</span>
              </button>
              <button
                type="button"
                onClick={() => setForm(prev => ({ ...prev, media_type: 'series' }))}
                className={`flex items-center justify-center gap-3 p-4 rounded-xl border-2 transition-all ${
                  form.media_type === 'series'
                    ? 'border-secondary-600 bg-secondary-50 text-secondary-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }`}
              >
                <Tv className="w-6 h-6" />
                <span className="font-medium text-lg">剧集</span>
              </button>
            </div>
          </div>

          {/* 基本信息 */}
          <div className="space-y-4">
            <h3 className="text-base font-semibold text-gray-800 border-b pb-2">基本信息</h3>

            <Input
              label="标题 *"
              name="title"
              value={form.title}
              onChange={handleChange}
              error={errors.title}
              placeholder="请输入电影/剧集标题"
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">简介</label>
              <textarea
                name="overview"
                value={form.overview}
                onChange={handleChange}
                rows={4}
                placeholder="请输入内容简介..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              />
            </div>

            <Input
              label="上映日期"
              name="release_date"
              type="date"
              value={form.release_date}
              onChange={handleChange}
            />
          </div>

          {/* 评分信息 */}
          <div className="space-y-4">
            <h3 className="text-base font-semibold text-gray-800 border-b pb-2 flex items-center gap-2">
              <Star className="w-4 h-4 text-yellow-500" />
              评分信息
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <Input
                label="评分 (0-10)"
                name="vote_average"
                type="number"
                value={form.vote_average}
                onChange={handleChange}
                error={errors.vote_average}
                placeholder="如：8.5"
              />
              <Input
                label="评分人数"
                name="vote_count"
                type="number"
                value={form.vote_count}
                onChange={handleChange}
                error={errors.vote_count}
                placeholder="如：10000"
              />
              <Input
                label="热度"
                name="popularity"
                type="number"
                value={form.popularity}
                onChange={handleChange}
                error={errors.popularity}
                placeholder="如：9.2"
              />
            </div>
          </div>

          {/* 类型标签 */}
          <div className="space-y-3">
            <h3 className="text-base font-semibold text-gray-800 border-b pb-2">类型标签</h3>
            <div className="flex flex-wrap gap-2">
              {GENRE_OPTIONS.map(g => (
                <button
                  key={g}
                  type="button"
                  onClick={() => toggleGenre(g)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                    form.genres.includes(g)
                      ? 'bg-primary-600 text-white shadow-sm'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {form.genres.includes(g) && <span className="mr-1">✓</span>}
                  {g}
                </button>
              ))}
            </div>
            {form.genres.length > 0 && (
              <p className="text-sm text-gray-500">已选：{form.genres.join('、')}</p>
            )}
          </div>

          {/* 图片链接 */}
          <div className="space-y-4">
            <h3 className="text-base font-semibold text-gray-800 border-b pb-2">图片链接（可选）</h3>
            <Input
              label="海报图片 URL"
              name="poster_path"
              value={form.poster_path}
              onChange={handleChange}
              placeholder="https://example.com/poster.jpg"
            />
            <Input
              label="背景图片 URL"
              name="backdrop_path"
              value={form.backdrop_path}
              onChange={handleChange}
              placeholder="https://example.com/backdrop.jpg"
            />

            {/* 海报预览 */}
            {form.poster_path && (
              <div className="mt-2">
                <p className="text-sm text-gray-500 mb-2">海报预览：</p>
                <img
                  src={form.poster_path}
                  alt="海报预览"
                  className="h-40 rounded-lg object-cover border border-gray-200"
                  onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
              </div>
            )}
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-4 pt-2">
            <Button
              type="submit"
              variant="primary"
              fullWidth
              isLoading={isLoading}
              disabled={isLoading || submitStatus === 'success'}
            >
              <PlusCircle className="w-4 h-4 mr-2" />
              {isLoading ? '提交中...' : '添加到数据库'}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleReset}
              disabled={isLoading}
            >
              重置
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
};

export default AddContent;
