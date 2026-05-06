import React from 'react';
import { clsx } from 'clsx';
import { User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface ChatBubbleProps {
  message: string;
  isUser: boolean;
  timestamp?: Date;
  isLoading?: boolean;
  isStreaming?: boolean;  // 正在流式输出中（显示闪烁光标）
}

const ChatBubble: React.FC<ChatBubbleProps> = ({
  message,
  isUser,
  timestamp,
  isLoading = false,
  isStreaming = false,
}) => {
  return (
    <div className={clsx('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* 头像 */}
      <div
        className={clsx(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-1',
          isUser ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'
        )}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* 消息气泡 */}
      <div className={clsx('flex flex-col max-w-[80%]', isUser ? 'items-end' : 'items-start')}>
        <div
          className={clsx(
            'rounded-2xl px-4 py-3',
            isUser
              ? 'bg-primary-600 text-white rounded-tr-none'
              : 'bg-gray-100 text-gray-900 rounded-tl-none'
          )}
        >
          {isLoading ? (
            <div className="flex items-center gap-2 py-1">
              <span className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <span
                    key={i}
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </span>
              <span className="text-gray-500 text-sm">思考中...</span>
            </div>
          ) : isUser ? (
            // 用户消息：纯文本
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{message}</p>
          ) : (
            // AI 消息：渲染 markdown + 流式光标
            <div className="prose prose-sm max-w-none text-gray-900
              prose-headings:text-gray-900 prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1
              prose-p:my-1 prose-p:leading-relaxed
              prose-strong:text-gray-900 prose-strong:font-semibold
              prose-ul:my-1 prose-ul:pl-4 prose-li:my-0.5
              prose-ol:my-1 prose-ol:pl-4
              prose-hr:my-2 prose-hr:border-gray-300
              prose-blockquote:border-l-2 prose-blockquote:border-gray-300 prose-blockquote:pl-3 prose-blockquote:text-gray-600
            ">
              {message ? (
                <>
                  <ReactMarkdown>{message}</ReactMarkdown>
                  {isStreaming && (
                    <span className="inline-block w-0.5 h-4 bg-gray-600 ml-0.5 animate-pulse align-middle" />
                  )}
                </>
              ) : isStreaming ? (
                // 空内容 + 流式中：只显示光标
                <span className="inline-block w-0.5 h-4 bg-gray-600 animate-pulse" />
              ) : null}
            </div>
          )}
        </div>

        {/* 时间戳 */}
        {timestamp && !isLoading && (
          <span className="text-xs text-gray-400 mt-1 px-1">
            {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
    </div>
  );
};

export default ChatBubble;
