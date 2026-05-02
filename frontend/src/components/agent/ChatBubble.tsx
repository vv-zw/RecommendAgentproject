import React from 'react';
import { clsx } from 'clsx';
import { User, Bot } from 'lucide-react';

interface ChatBubbleProps {
  message: string;
  isUser: boolean;
  timestamp?: Date;
  isLoading?: boolean;
}

const ChatBubble: React.FC<ChatBubbleProps> = ({
  message,
  isUser,
  timestamp,
  isLoading = false,
}) => {
  return (
    <div
      className={clsx(
        'flex gap-3 mb-4',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* 头像 */}
      <div
        className={clsx(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-200 text-gray-700'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : (
          <Bot className="w-4 h-4" />
        )}
      </div>

      {/* 消息气泡 */}
      <div className="flex-1">
        <div
          className={clsx(
            'rounded-2xl px-4 py-3 max-w-[80%]',
            isUser
              ? 'bg-primary-100 text-primary-900 rounded-tr-none ml-auto'
              : 'bg-gray-100 text-gray-900 rounded-tl-none'
          )}
        >
          {isLoading ? (
            <div className="flex items-center gap-2">
              <div className="animate-pulse flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
              </div>
              <span className="text-gray-500">思考中...</span>
            </div>
          ) : (
            <div className="whitespace-pre-wrap">{message}</div>
          )}
        </div>

        {/* 时间戳 */}
        {timestamp && (
          <div
            className={clsx(
              'text-xs text-gray-500 mt-1',
              isUser ? 'text-right' : 'text-left'
            )}
          >
            {timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatBubble;