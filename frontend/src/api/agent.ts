import api from './index';
import { MediaItem } from './content';

export interface AgentChatResponse {
  nl_response: string;
  structured_results: MediaItem[];
  session_id: string;
}

// SSE 流式回调类型
export interface StreamCallbacks {
  onMeta: (sessionId: string, results: MediaItem[]) => void;  // 收到 meta 帧（session_id + 推荐结果）
  onToken: (token: string) => void;                           // 收到文本 token
  onDone: () => void;                                         // 流结束
  onError: (err: string) => void;                             // 出错
}

export const agentApi = {
  /**
   * 普通 JSON 模式（非流式）
   */
  chat: async (message: string, sessionId?: string): Promise<AgentChatResponse> => {
    const response = await api.post<AgentChatResponse>('/agent/chat', {
      message,
      session_id: sessionId ?? null,
      stream: false,
    });
    return response.data;
  },

  /**
   * SSE 流式模式
   * 使用 fetch + ReadableStream 接收逐 token 推送
   * 返回 AbortController，调用方可用于取消请求
   */
  chatStream: (
    message: string,
    callbacks: StreamCallbacks,
    sessionId?: string,
  ): AbortController => {
    const controller = new AbortController();

    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    const baseUrl = (import.meta as any).env?.VITE_API_BASE_URL || '';

    fetch(`${baseUrl}/api/agent/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-access-token': token,
      },
      body: JSON.stringify({
        message,
        session_id: sessionId ?? null,
        stream: true,
      }),
      signal: controller.signal,
    })
      .then(async res => {
        if (!res.ok) {
          callbacks.onError(`HTTP ${res.status}`);
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          callbacks.onError('无法读取响应流');
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // 按行解析 SSE 事件（格式：data: {...}\n\n）
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';  // 最后一行可能不完整，留到下次

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith('data:')) continue;

            const data = trimmed.slice(5).trim();

            if (data === '[DONE]') {
              callbacks.onDone();
              return;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.type === 'meta') {
                callbacks.onMeta(parsed.session_id, parsed.structured_results ?? []);
              } else if (parsed.type === 'token') {
                callbacks.onToken(parsed.content ?? '');
              } else if (parsed.type === 'error') {
                callbacks.onError(parsed.message ?? '未知错误');
              }
            } catch {
              // 忽略解析失败的行
            }
          }
        }

        callbacks.onDone();
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          callbacks.onError(err.message ?? '网络错误');
        }
      });

    return controller;
  },

  healthCheck: async () => {
    const response = await api.get<{ status: string; timestamp: string }>('/health');
    return response.data;
  },
};
