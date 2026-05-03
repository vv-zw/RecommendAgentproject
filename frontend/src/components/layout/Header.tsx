import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Film, Search, User, LogOut, Menu, X, Bot, PlusCircle } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import Button from '../common/Button';
import { useUIStore } from '../../store/uiStore';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuthStore();
  const { sidebarOpen, toggleSidebar } = useUIStore();

  const navItems = [
    { name: '首页', path: '/' },
    { name: '电影', path: '/movies' },
    { name: '剧集', path: '/series' },
    { name: '待看清单', path: '/watchlist' },
    { name: 'AI助手', path: '/agent', icon: <Bot className="w-4 h-4" /> },
    { name: '添加影视', path: '/add-content', icon: <PlusCircle className="w-4 h-4" /> },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* 左侧：Logo和导航 */}
          <div className="flex items-center gap-8">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <Film className="w-8 h-8 text-primary-600" />
              <span className="text-xl font-bold text-gray-900">
                Movie<span className="text-primary-600">AI</span>
              </span>
            </Link>

            {/* 桌面导航 */}
            <nav className="hidden md:flex items-center gap-6">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className="flex items-center gap-2 text-gray-700 hover:text-primary-600 transition-colors"
                >
                  {item.icon}
                  {item.name}
                </Link>
              ))}
            </nav>
          </div>

          {/* 右侧：搜索和用户 */}
          <div className="flex items-center gap-4">
            {/* 搜索按钮 */}
            <button
              onClick={() => navigate('/search')}
              className="p-2 text-gray-600 hover:text-primary-600 transition-colors"
            >
              <Search className="w-5 h-5" />
            </button>

            {/* 用户菜单 */}
            {isAuthenticated ? (
              <div className="relative group">
                <button className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 transition-colors">
                  <User className="w-5 h-5 text-gray-600" />
                  <span className="hidden md:inline text-sm font-medium">
                    我的账户
                  </span>
                </button>
                
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
                  <div className="py-2">
                    <Link
                      to="/profile"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      个人资料
                    </Link>
                    <Link
                      to="/watchlist"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      待看清单
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                    >
                      <LogOut className="w-4 h-4" />
                      退出登录
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate('/login')}
                >
                  登录
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => navigate('/register')}
                >
                  注册
                </Button>
              </div>
            )}

            {/* 移动端菜单按钮 */}
            <button
              onClick={toggleSidebar}
              className="md:hidden p-2 text-gray-600 hover:text-primary-600"
            >
              {sidebarOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 移动端侧边栏 */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-50">
          {/* 遮罩 */}
          <div
            className="absolute inset-0 bg-black/50"
            onClick={toggleSidebar}
          />
          
          {/* 侧边栏内容 */}
          <div className="absolute right-0 top-0 bottom-0 w-64 bg-white shadow-xl">
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <span className="text-lg font-semibold">菜单</span>
                <button
                  onClick={toggleSidebar}
                  className="p-2 text-gray-600 hover:text-primary-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>
            
            <nav className="p-4">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-100 text-gray-700 mb-2"
                  onClick={toggleSidebar}
                >
                  {item.icon}
                  {item.name}
                </Link>
              ))}
              
              {isAuthenticated ? (
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-3 w-full px-4 py-3 rounded-lg hover:bg-red-50 text-red-600 mt-4"
                >
                  <LogOut className="w-5 h-5" />
                  退出登录
                </button>
              ) : (
                <div className="mt-4 space-y-2">
                  <Button
                    variant="outline"
                    fullWidth
                    onClick={() => {
                      navigate('/login');
                      toggleSidebar();
                    }}
                  >
                    登录
                  </Button>
                  <Button
                    variant="primary"
                    fullWidth
                    onClick={() => {
                      navigate('/register');
                      toggleSidebar();
                    }}
                  >
                    注册
                  </Button>
                </div>
              )}
            </nav>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;