import React, { useState } from 'react';
import { Send, Sparkles } from 'lucide-react';
import Button from '../common/Button';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  placeholder?: string;
  disabled?: boolean;
  isLoading?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  placeholder = '输入您的问题，例如：推荐类似流浪地球的电影...',
  disabled = false,
  isLoading = false,
}) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled && !isLoading) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const examplePrompts = [
    '推荐类似流浪地球的电影',
    '最近有什么高分科幻片',
    '我想看轻松一点的剧',
    '推荐适合家庭观看的电影',
    '有什么悬疑惊悚剧推荐',
  ];

  return (
    <div className="space-y-4">
      {/* 示例提示 */}
      <div className="flex flex-wrap gap-2">
        {examplePrompts.map((prompt, index) => (
          <button
            key={index}
            type="button"
            onClick={() => {
              setMessage(prompt);
              setTimeout(() => {
                const textarea = document.querySelector('textarea');
                if (textarea) {
                  textarea.focus();
                }
              }, 0);
            }}
            className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
            disabled={disabled || isLoading}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* 输入框 */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isLoading}
            className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none disabled:bg-gray-100 disabled:cursor-not-allowed"
            rows={3}
          />
          
          <div className="absolute right-2 bottom-2">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={!message.trim() || disabled || isLoading}
              isLoading={isLoading}
              className="rounded-full"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* AI助手提示 */}
        <div className="flex items-center gap-2 mt-2 text-sm text-gray-500">
          <Sparkles className="w-4 h-4" />
          <span>AI助手会根据您的描述智能推荐影视内容</span>
        </div>
      </form>
    </div>
  );
};

export default ChatInput;