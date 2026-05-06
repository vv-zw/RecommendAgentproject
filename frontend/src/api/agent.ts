import api from './index';
import { MediaItem } from './content';

export interface AgentChatResponse {
  nl_response: string;
  structured_results: MediaItem[];
  session_id: string;
}

export const agentApi = {
  /**
   * 发送消息给 AI Agent，支持多轮对话（传入 session_id）
   */
  chat: async (message: string, sessionId?: string): Promise<AgentChatResponse> => {
    const response = await api.post<AgentChatResponse>('/agent/chat', {
      message,
      session_id: sessionId ?? null,
    });
    return response.data;
  },

  healthCheck: async () => {
    const response = await api.get<{ status: string; timestamp: string }>('/health');
    return response.data;
  },
};
