# 影视推荐AI助手 - 前端应用

基于React的现代化影视推荐系统前端，集成AI智能对话推荐功能。

## 🚀 快速启动

### 1. 安装依赖
```bash
cd frontend
npm install
```

### 2. 启动开发服务器
```bash
npm run dev
```

前端应用将在 **http://localhost:3000** 启动

### 3. 启动后端API服务器
确保后端API服务正在运行：
```bash
# 在项目根目录
python api/app.py
```

后端API将在 **http://localhost:5001** 启动

## 📁 项目结构

```
frontend/
├── src/
│   ├── api/                    # API客户端
│   │   ├── index.ts           # Axios配置
│   │   ├── auth.ts            # 认证API
│   │   ├── content.ts         # 内容API
│   │   └── agent.ts           # AI Agent API
│   ├── components/            # 可复用组件
│   │   ├── common/           # 通用组件
│   │   ├── layout/           # 布局组件
│   │   ├── media/            # 媒体相关组件
│   │   └── agent/            # AI助手组件
│   ├── pages/                # 页面组件
│   │   ├── Home.tsx          # 首页
│   │   ├── Movies.tsx        # 电影页
│   │   ├── Series.tsx        # 剧集页
│   │   ├── Watchlist.tsx     # 待看清单
│   │   ├── AgentAssistant.tsx # AI助手页
│   │   ├── Login.tsx         # 登录页
│   │   └── Register.tsx      # 注册页
│   ├── store/                # 状态管理
│   │   ├── authStore.ts      # 认证状态
│   │   └── uiStore.ts        # UI状态
│   ├── App.tsx              # 主应用组件
│   └── main.tsx             # 应用入口
├── public/                  # 静态资源
├── index.html              # HTML模板
└── package.json            # 依赖配置
```

## 🔧 技术栈

- **React 18** - UI框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **TailwindCSS** - 样式框架
- **React Router** - 路由管理
- **Axios** - HTTP客户端
- **React Query** - 数据获取
- **Zustand** - 状态管理
- **Lucide React** - 图标库

## 🌐 API代理配置

前端通过Vite代理连接到后端API：

```javascript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:5001',  // 后端API地址
    changeOrigin: true,
  }
}
```

## 📱 核心功能

### 1. AI智能助手
- 自然语言对话界面
- 智能影视推荐
- 推荐理由展示
- 对话历史记录

### 2. 影视浏览
- 电影/剧集分类浏览
- 分页加载
- 筛选和排序
- 详情查看

### 3. 用户功能
- 用户注册/登录
- 待看清单管理
- 观看历史记录
- 个性化推荐

### 4. 响应式设计
- 移动端适配
- 现代化UI组件
- 流畅动画效果

## 🎨 UI设计特点

- Netflix + ChatGPT结合风格
- 现代化卡片设计
- 深色/浅色主题支持
- 流畅的交互动画
- 直观的用户引导

## 🔒 认证流程

1. 用户注册/登录获取JWT token
2. Token存储在localStorage
3. 所有API请求自动携带token
4. Token过期自动跳转登录页

## 🚦 开发命令

```bash
# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview

# 代码检查
npm run lint
```

## 📊 环境要求

- Node.js 18+
- npm 9+
- 后端API服务运行在端口5001

## 🔗 API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/register` | POST | 用户注册 |
| `/api/movies` | GET | 获取电影列表 |
| `/api/series` | GET | 获取剧集列表 |
| `/api/agent/chat` | POST | AI对话推荐 |
| `/api/users/{id}/watchlist` | GET | 获取待看清单 |
| `/api/users/{id}/watchlist` | POST | 添加到待看清单 |

## 🎯 下一步计划

1. 集成真实API数据
2. 添加搜索功能
3. 实现用户偏好设置
4. 添加评分和评论功能
5. 优化移动端体验
6. 添加PWA支持

## 📝 注意事项

1. 确保后端API服务已启动
2. 首次使用需要注册账户
3. AI助手功能需要用户登录
4. 开发模式下使用代理避免CORS问题