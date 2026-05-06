import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Bot, Sparkles, RefreshCw, Trash2 } from 'lucide-react';
import ChatBubble from '../components/agent/ChatBubble';
import ChatInput from '../components/agent/ChatInput';
import RecommendationCard from '../components/agent/RecommendationCard';
import { agentApi } from '../api/agent';
import { contentApi, UserPreference, MediaItem } from '../api/content';
import { useAuthStore } from '../store/authStore';

// 默认快捷词条（未登录或偏好加载失败时使用）
const DEFAULT_QUICK_PROMPTS = [
  '推荐类似流浪地球的电影',
  '最近有什么高分科幻片',
  '我想看轻松治愈的剧',
  '推荐适合家庭观看的电影',
  '有什么悬疑惊悚剧推荐',
];

function generateQuickPrompts(preferences: UserPreference[]): string[] {
  const prompts: string[] = [];
  const genres = new Set<string>();
  const directors = new Set<string>();
  const actors = new Set<string>();

  for (const pref of preferences) {
    if (pref.genres) pref.genres.split('/').forEach(g => g.trim() && genres.add(g.trim()));
    if (pref.director?.trim()) directors.add(pref.director.trim());
    if (pref.actors) pref.actors.split('/').forEach(a => a.trim() && actors.add(a.trim()));
  }

  Array.from(genres).slice(0, 2).forEach(g => prompts.push(`推荐更多${g}电影`));
  Array.from(directors).slice(0, 1).forEach(d => prompts.push(`推荐${d}的其他作品`));
  Array.from(actors).slice(0, 1).forEach(a => prompts.push(`推荐${a}主演的其他影视`));

  const fallbacks = ['最近有什么高分电影', '推荐经典动作片', '有什么好看的悬疑剧', '推荐温暖治愈的剧集'];
  let i = 0;
  while (prompts.length < 4 && i < fallbacks.length) prompts.push(fallbacks[i++]);

  return prompts;
}

interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  isLoading?: boolean;
}

const WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome',
  content: '您好！我是您的影视推荐 AI 助手 🎬\n\n可以问我：\n- **推荐类似《流浪地球》的电影**\n- **最近有什么高分科幻片**\n- **我想看轻松治愈的剧**\n\n试试下方的快捷词条，或者直接输入您的需求！',
  isUser: false,
  timestamp: new Date(),
};

const AgentAssistant: React.FC = () => {
  const { isAuthenticated, user } = useAuthStore();
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [recommendations, setRecommendations] = useState<MediaItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [quickPrompts, setQuickPrompts] = useState<string[]>(DEFAULT_QUICK_PROMPTS);
  const [promptsLoading, setPromptsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // 加载用户偏好，生成个性化快捷词条
  useEffect(() => {
    if (!isAuthenticated || !user) {
      setQuickPrompts(DEFAULT_QUICK_PROMPTS);
      return;
    }
    setPromptsLoading(true);
    contentApi.getUserPreferences(user.id)
      .then(data => {
        if (data.preferences?.length > 0) {
          setQuickPrompts(generateQuickPrompts(data.preferences));
        } else {
          setQuickPrompts(DEFAULT_QUICK_PROMPTS);
        }
      })
      .catch(() => setQuickPrompts(DEFAULT_QUICK_PROMPTS))
      .finally(() => setPromptsLoading(false));
  }, [isAuthenticated, user]);

  // 新消息时滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSendMessage = async (message: string) => {
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      content: message,
      isUser: true,
      timestamp: new Date(),
    };
    const thinkingId = `t-${Date.now()}`;
    const thinkingMsg: ChatMessage = {
      id: thinkingId,
      content: '',
      isUser: false,
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages(prev => [...prev, userMsg, thinkingMsg]);
    setIsLoading(true);

    try {
      const response = await agentApi.chat(message, sessionId ?? undefined);

      // 保存 session_id 用于多轮对话
      if (response.session_id) {
        setSessionId(response.session_id);
      }

      setMessages(prev => [
        ...prev.filter(m => m.id !== thinkingId),
        {
          id: `a-${Date.now()}`,
          content: response.nl_response,
          isUser: false,
          timestamp: new Date(),
        },
      ]);

      if (response.structured_results?.length > 0) {
        setRecommendations(response.structured_results);
      }
    } catch (error) {
      console.error('AI 对话失败:', error);
      setMessages(prev => [
        ...prev.filter(m => m.id !== thinkingId),
        {
          id: `e-${Date.now()}`,
          content: '抱歉，处理您的请求时出现了问题，请稍后重试。',
          isUser: false,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([WELCOME_MESSAGE]);
    setRecommendations([]);
    setSessionId(null);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] gap-4">
      {/* 页头 */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary-100 rounded-xl">
            <Bot className="w-6 h-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">AI 助手</h1>
            <p className="text-sm text-gray-500">
              {isAuthenticated ? '基于您的偏好，智能推荐影视内容' : '智能影视推荐对话助手'}
            </p>
          </div>
        </div>
        <button
          onClick={handleClearChat}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          清空对话
        </button>
      </div>

      {/* 主体：聊天 + 推荐结果 */}
      <div className="flex gap-4 flex-1 min-h-0">

        {/* 左侧：聊天区域 */}
        <div className="flex flex-col flex-1 min-w-0 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">

          {/* 消息列表 — 可滚动区域 */}
          <div
            ref={messagesContainerRef}
            className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scroll-smooth"
          >
            {messages.map(msg => (
              <ChatBubble
                key={msg.id}
                message={msg.content}
                isUser={msg.isUser}
                timestamp={msg.timestamp}
                isLoading={msg.isLoading}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* 底部输入区域 */}
          <div className="flex-shrink-0 border-t border-gray-100 px-4 pt-3 pb-4 space-y-3">
            {/* 快捷词条 */}
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-primary-500" />
                <span className="text-xs text-gray-400">
                  {isAuthenticated && !promptsLoading ? '基于您的偏好' : '快捷提示'}
                </span>
                {promptsLoading && (
                  <RefreshCw className="w-3 h-3 text-gray-300 animate-spin" />
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {quickPrompts.map((prompt, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleSendMessage(prompt)}
                    disabled={isLoading}
                    className="px-3 py-1 text-xs bg-gray-50 hover:bg-primary-50 hover:text-primary-700 text-gray-600 border border-gray-200 hover:border-primary-200 rounded-full transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>

            {/* 输入框 */}
            <ChatInput
              onSendMessage={handleSendMessage}
              disabled={isLoading}
              isLoading={isLoading}
            />
          </div>
        </div>

        {/* 右侧：推荐结果 */}
        <div className="w-80 flex-shrink-0 flex flex-col bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 flex-shrink-0">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary-600" />
              <h2 className="text-sm font-semibold text-gray-900">推荐结果</h2>
            </div>
            {recommendations.length > 0 && (
              <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                {recommendations.length} 部
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto">
            {recommendations.length > 0 ? (
              <div className="p-3 space-y-2">
                {recommendations.map((item, index) => (
                  <RecommendationCard
                    key={item.id}
                    item={item}
                    rank={index + 1}
                    reason={item.explanation}
                  />
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center px-6 py-12">
                <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
                  <Sparkles className="w-6 h-6 text-gray-300" />
                </div>
                <p className="text-sm text-gray-500">暂无推荐结果</p>
                <p className="text-xs text-gray-400 mt-1">开始对话后，推荐内容会显示在这里</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentAssistant;
