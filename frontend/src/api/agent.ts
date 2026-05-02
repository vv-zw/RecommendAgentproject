import api from './index';
import { MediaItem } from './content';

export interface AgentChatRequest {
  message: string;
}

export interface AgentChatResponse {
  nl_response: string;
  structured_results: MediaItem[];
}

export interface RecommendationResult {
  answer: string;
  results: MediaItem[];
}

export const agentApi = {
  // AI Agent聊天推荐
  chat: async (message: string) => {
    const userId = localStorage.getItem('user_id');
    if (!userId) {
      throw new Error('User not authenticated');
    }

    const response = await api.post<AgentChatResponse>('/agent/chat', {
      message,
    });
    return response.data;
  },

  // 健康检查
  healthCheck: async () => {
    const response = await api.get<{ status: string; timestamp: string }>('/health');
    return response.data;
  },
};