import React, { useState, useRef, useEffect } from 'react';
import { Bot, Sparkles, RefreshCw } from 'lucide-react';
import ChatBubble from '../components/agent/ChatBubble';
import ChatInput from '../components/agent/ChatInput';
import RecommendationCard from '../components/agent/RecommendationCard';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import { agentApi } from '../api/agent';
import { contentApi, UserPreference, MediaItem } from '../api/content';
import { useAuthStore } from '../store/authStore';

// 默认快捷词条（未登录或偏好加载失败时使用）
const DEFAULT_QUICK_PROMPTS = [
  '推荐类似流浪地球的电影',
  '最近有什么高分科幻片',
  '我想看轻松一点的剧',
  '推荐适合家庭观看的电影',
  '有什么悬疑惊悚剧推荐',
];

/**
 * 根据用户偏好数据生成个性化快捷词条
 */
function generateQuickPrompts(preferences: UserPreference[]): string[] {
  const prompts: string[] = [];
  const genres = new Set<string>();
  const directors = new Set<string>();
  const actors = new Set<string>();

  for (const pref of preferences) {
    if (pref.genres) {
      pref.genres.split('/').forEach(g => { if (g.trim()) genres.add(g.trim()); });
    }
    if (pref.director?.trim()) directors.add(pref.director.trim());
    if (pref.actors) {
      pref.actors.split('/').forEach(a => { if (a.trim()) actors.add(a.trim()); });
    }
  }

  // 基于类型生成词条（最多2个）
  Array.from(genres).slice(0, 2).forEach(g => {
    prompts.push(`推荐更多${g}电影`);
  });

  // 基于导演生成词条（最多1个）
  Array.from(directors).slice(0, 1).forEach(d => {
    prompts.push(`推荐${d}的其他作品`);
  });

  // 基于演员生成词条（最多1个）
  Array.from(actors).slice(0, 1).forEach(a => {
    prompts.push(`推荐${a}主演的其他影视`);
  });

  // 补充通用词条，确保至少有4个
  const fallbackPrompts = ['最近有什么高分电影', '推荐经典动作片', '有什么好看的悬疑剧'];
  let i = 0;
  while (prompts.length < 4 && i < fallbackPrompts.length) {
    prompts.push(fallbackPrompts[i++]);
  }

  return prompts;
}

interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  isLoading?: boolean;
}

const AgentAssistant: React.FC = () => {
  const { isAuthenticated, user } = useAuthStore();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: '您好！我是您的影视推荐AI助手。您可以问我类似："推荐类似流浪地球的电影"、"最近有什么高分科幻片"、"我想看轻松一点的剧"等问题。',
      isUser: false,
      timestamp: new Date(),
    },
  ]);
  const [recommendations, setRecommendations] = useState<MediaItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [quickPrompts, setQuickPrompts] = useState<string[]>(DEFAULT_QUICK_PROMPTS);
  const [promptsLoading, setPromptsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 加载用户偏好，生成个性化快捷词条
  useEffect(() => {
    if (!isAuthenticated || !user) {
      setQuickPrompts(DEFAULT_QUICK_PROMPTS);
      return;
    }

    setPromptsLoading(true);
    contentApi.getUserPreferences(user.id)
      .then(data => {
        if (data.preferences && data.preferences.length > 0) {
          const generated = generateQuickPrompts(data.preferences);
          setQuickPrompts(generated);
        } else {
          setQuickPrompts(DEFAULT_QUICK_PROMPTS);
        }
      })
      .catch(() => {
        // 静默失败，保留默认词条
        setQuickPrompts(DEFAULT_QUICK_PROMPTS);
      })
      .finally(() => {
        setPromptsLoading(false);
      });
  }, [isAuthenticated, user]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (message: string) => {
    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: message,
      isUser: true,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);

    // 添加 AI 思考中消息
    const thinkingId = (Date.now() + 1).toString();
    const thinkingMessage: ChatMessage = {
      id: thinkingId,
      content: '正在为您分析...',
      isUser: false,
      timestamp: new Date(),
      isLoading: true,
    };
    setMessages(prev => [...prev, thinkingMessage]);
    setIsLoading(true);

    try {
      const response = await agentApi.chat(message);

      // 移除思考消息，添加 AI 回复
      setMessages(prev => [
        ...prev.filter(msg => msg.id !== thinkingId),
        {
          id: Date.now().toString(),
          content: response.nl_response,
          isUser: false,
          timestamp: new Date(),
        },
      ]);

      if (response.structured_results && response.structured_results.length > 0) {
        setRecommendations(response.structured_results);
      }
    } catch (error) {
      console.error('AI对话失败:', error);
      setMessages(prev => [
        ...prev.filter(msg => msg.id !== thinkingId),
        {
          id: Date.now().toString(),
          content: '抱歉，处理您的请求时出现了问题。请稍后重试。',
          isUser: false,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: '1',
        content: '您好！我是您的影视推荐AI助手。您可以问我类似："推荐类似流浪地球的电影"、"最近有什么高分科幻片"、"我想看轻松一点的剧"等问题。',
        isUser: false,
        timestamp: new Date(),
      },
    ]);
    setRecommendations([]);
  };

  return (
    <div className="space-y-8">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary-100 rounded-full">
            <Bot className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">AI助手</h1>
            <p className="text-gray-600">
              {isAuthenticated ? '基于您的偏好，智能推荐影视内容' : '智能影视推荐对话助手'}
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={clearChat}>
          清空对话
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* 聊天区域 */}
        <div className="lg:col-span-2">
          <Card className="h-[600px] flex flex-col">
            {/* 消息列表 */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-4">
                {messages.map((message) => (
                  <ChatBubble
                    key={message.id}
                    message={message.content}
                    isUser={message.isUser}
                    timestamp={message.timestamp}
                    isLoading={message.isLoading}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* 输入区域 */}
            <div className="border-t border-gray-200 p-6">
              {/* 快捷词条 */}
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-primary-500" />
                  <span className="text-xs text-gray-500">
                    {isAuthenticated && !promptsLoading ? '基于您的偏好推荐' : '快捷提示'}
                  </span>
                  {isAuthenticated && promptsLoading && (
                    <RefreshCw className="w-3 h-3 text-gray-400 animate-spin" />
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {quickPrompts.map((prompt, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() => handleSendMessage(prompt)}
                      disabled={isLoading}
                      className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-primary-50 hover:text-primary-700 text-gray-700 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>

              <ChatInput
                onSendMessage={handleSendMessage}
                disabled={isLoading}
                isLoading={isLoading}
              />
            </div>
          </Card>
        </div>

        {/* 推荐结果区域 */}
        <div>
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-primary-600" />
              <h2 className="text-xl font-semibold text-gray-900">推荐结果</h2>
              {recommendations.length > 0 && (
                <span className="ml-auto text-sm text-gray-500">
                  {recommendations.length} 个结果
                </span>
              )}
            </div>

            {recommendations.length > 0 ? (
              <div className="space-y-4 max-h-[500px] overflow-y-auto">
                {recommendations.map((item, index) => (
                  <RecommendationCard
                    key={item.id}
                    item={item}
                    rank={index + 1}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Sparkles className="w-12 h-12 mx-auto text-gray-300 mb-4" />
                <p className="text-gray-600">暂无推荐结果</p>
                <p className="text-sm text-gray-500 mt-2">开始对话获取AI推荐</p>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AgentAssistant;
