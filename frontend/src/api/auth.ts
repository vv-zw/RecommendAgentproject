import api from './index';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest extends LoginRequest {
  email: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
}

export const authApi = {
  // 用户注册
  register: async (data: RegisterRequest) => {
    const response = await api.post<{ message: string; user_id: number }>('/auth/register', data);
    return response.data;
  },

  // 用户登录
  login: async (data: LoginRequest) => {
    const response = await api.post<AuthResponse>('/auth/login', data);
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('user_id', response.data.user_id.toString());
    }
    return response.data;
  },

  // 用户登出
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
  },

  // 获取当前用户信息
  getCurrentUser: () => {
    const userId = localStorage.getItem('user_id');
    return userId ? parseInt(userId) : null;
  },

  // 检查是否已登录
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  },
};