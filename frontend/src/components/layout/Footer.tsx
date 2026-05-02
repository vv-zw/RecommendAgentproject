import React from 'react';
import { Link } from 'react-router-dom';
import { Film, Github, Twitter, Mail } from 'lucide-react';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-gray-900 text-white mt-16">
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Logo和描述 */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <Film className="w-8 h-8 text-primary-400" />
              <span className="text-2xl font-bold">
                Movie<span className="text-primary-400">AI</span>
              </span>
            </div>
            <p className="text-gray-400 mb-6 max-w-md">
              基于AI技术的智能影视推荐平台，为您提供个性化的观影建议和智能对话体验。
            </p>
            <div className="flex gap-4">
              <a
                href="#"
                className="p-2 bg-gray-800 rounded-full hover:bg-gray-700 transition-colors"
              >
                <Github className="w-5 h-5" />
              </a>
              <a
                href="#"
                className="p-2 bg-gray-800 rounded-full hover:bg-gray-700 transition-colors"
              >
                <Twitter className="w-5 h-5" />
              </a>
              <a
                href="#"
                className="p-2 bg-gray-800 rounded-full hover:bg-gray-700 transition-colors"
              >
                <Mail className="w-5 h-5" />
              </a>
            </div>
          </div>

          {/* 快速链接 */}
          <div>
            <h3 className="text-lg font-semibold mb-4">快速链接</h3>
            <ul className="space-y-2">
              <li>
                <Link
                  to="/movies"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  电影库
                </Link>
              </li>
              <li>
                <Link
                  to="/series"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  剧集库
                </Link>
              </li>
              <li>
                <Link
                  to="/watchlist"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  待看清单
                </Link>
              </li>
              <li>
                <Link
                  to="/agent"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  AI助手
                </Link>
              </li>
            </ul>
          </div>

          {/* 技术支持 */}
          <div>
            <h3 className="text-lg font-semibold mb-4">技术支持</h3>
            <ul className="space-y-2">
              <li>
                <a
                  href="#"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  帮助中心
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  常见问题
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  联系我们
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  隐私政策
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* 版权信息 */}
        <div className="border-t border-gray-800 mt-8 pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <p className="text-gray-400 text-sm">
              © {currentYear} MovieAI. All rights reserved.
            </p>
            <p className="text-gray-400 text-sm mt-2 md:mt-0">
              基于AI技术的智能推荐系统
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;