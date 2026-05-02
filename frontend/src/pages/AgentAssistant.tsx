import React, { useState, useRef, useEffect } from 'react';
import { Bot, Sparkles } from 'lucide-react';
import ChatBubble from '../components/agent/ChatBubble';
import ChatInput from '../components/agent/ChatInput';
import RecommendationCard from '../components/agent/RecommendationCard';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import { agentApi } from '../api/agent';
import { MediaItem } from '../api/content';

interface ChatMessage {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
}

const AgentAssistant: React.FC = () => {
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
    setMessages((prev) => [...prev, userMessage]);

    // 添加AI思考消息
    const thinkingMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      content: '正在为您分析...',
      isUser: false,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, thinkingMessage]);

    setIsLoading(true);

    try {
      const response = await agentApi.chat(message);
      
      // 移除思考消息
      setMessages((prev) => prev.filter(msg => msg.id !== thinkingMessage.id));
      
      // 添加AI回复
      const aiMessage: ChatMessage = {
        id: Date.now().toString(),
        content: response.nl_response,
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
      
      // 设置推荐结果
      if (response.structured_results && response.structured_results.length > 0) {
        setRecommendations(response.structured_results);
      }
    } catch (error) {
      console.error('AI对话失败:', error);
      
      // 移除思考消息
      setMessages((prev) => prev.filter(msg => msg.id !== thinkingMessage.id));
      
      // 添加错误消息
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        content: '抱歉，处理您的请求时出现了问题。请稍后重试。',
        isUser: false,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary-100 rounded-full">
            <Bot className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">AI助手</h1>
            <p className="text-gray-600">智能影视推荐对话助手</p>
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
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-4">
                {messages.map((message) => (
                  <ChatBubble
                    key={message.id}
                    message={message.content}
                    isUser={message.isUser}
                    timestamp={message.timestamp}
                    isLoading={message.content === '正在为您分析...'}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>
            
            <div className="border-t border-gray-200 p-6">
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
          <Card>
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
              <div className="space-y-4">
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
                <div className="text-gray-400 mb-4">
                  <Sparkles className="w-12 h-12 mx-auto" />
                </div>
                <p className="text-gray-600">暂无推荐结果</p>
                <p className="text-sm text-gray-500 mt-2">
                  开始对话获取AI推荐
                </p>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AgentAssistant;