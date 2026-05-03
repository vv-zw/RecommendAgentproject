import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { UserPlus } from 'lucide-react';
import Card from '../components/common/Card';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { authApi } from '../api/auth';
import { useAuthStore } from '../store/authStore';

const Register: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.username.trim()) {
      newErrors.username = '请输入用户名';
    } else if (formData.username.length < 3) {
      newErrors.username = '用户名至少3位';
    }

    if (!formData.email.trim()) {
      newErrors.email = '请输入邮箱';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = '邮箱格式不正确';
    }

    if (!formData.password) {
      newErrors.password = '请输入密码';
    } else if (formData.password.length < 6) {
      newErrors.password = '密码至少6位';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = '请确认密码';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = '两次输入的密码不一致';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setIsLoading(true);
    try {
      // 第一步：调用注册 API
      await authApi.register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
      });

      // 第二步：注册成功后自动登录
      const loginResponse = await authApi.login({
        username: formData.username,
        password: formData.password,
      });

      // 第三步：更新全局状态
      login(
        { id: loginResponse.user_id, username: formData.username, email: formData.email },
        loginResponse.access_token
      );

      // 第四步：跳转首页
      navigate('/');
    } catch (error: unknown) {
      console.error('注册失败:', error);
      const axiosError = error as { response?: { data?: { error?: string } } };
      setErrors({
        submit: axiosError.response?.data?.error || '注册失败，请稍后重试',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-12">
      <Card className="p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
            <UserPlus className="w-8 h-8 text-primary-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">注册新账户</h1>
          <p className="text-gray-600 mt-2">创建账户以使用AI推荐功能</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            label="用户名"
            name="username"
            value={formData.username}
            onChange={handleChange}
            error={errors.username}
            placeholder="请输入用户名（至少3位）"
            required
          />

          <Input
            label="邮箱"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            error={errors.email}
            placeholder="请输入邮箱"
            required
          />

          <Input
            label="密码"
            name="password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            error={errors.password}
            placeholder="请输入密码（至少6位）"
            required
          />

          <Input
            label="确认密码"
            name="confirmPassword"
            type="password"
            value={formData.confirmPassword}
            onChange={handleChange}
            error={errors.confirmPassword}
            placeholder="请再次输入密码"
            required
          />

          {errors.submit && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{errors.submit}</p>
            </div>
          )}

          <div className="flex items-center">
            <input
              type="checkbox"
              id="terms"
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              required
            />
            <label htmlFor="terms" className="ml-2 block text-sm text-gray-700">
              我同意{' '}
              <a href="#" className="text-primary-600 hover:text-primary-500">服务条款</a>
              {' '}和{' '}
              <a href="#" className="text-primary-600 hover:text-primary-500">隐私政策</a>
            </label>
          </div>

          <Button type="submit" variant="primary" fullWidth isLoading={isLoading} disabled={isLoading}>
            注册
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-600">
            已有账户？{' '}
            <Link to="/login" className="text-primary-600 hover:text-primary-500 font-medium">
              立即登录
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
};

export default Register;
