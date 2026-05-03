# 实现任务列表：media-search-add-detail

## 任务

- [x] 1. 后端新增接口（api/routes.py）
  - [x] 1.1 新增 preference_to_media 和 content_item_to_media_detail 工具函数
  - [x] 1.2 新增 GET /api/content/{id} 通用详情接口
  - [x] 1.3 新增 POST /api/users/{user_id}/library 添加影片到影片库接口
  - [x] 1.4 新增 GET /api/users/{user_id}/library/movies 获取用户电影库接口
  - [x] 1.5 新增 GET /api/users/{user_id}/library/series 获取用户剧集库接口

- [x] 2. 前端 API 层扩展（frontend/src/api/content.ts）
  - [x] 2.1 新增 ContentDetail、LibraryAddRequest、ReviewItem、CastMember 类型
  - [x] 2.2 新增 addToLibrary、getLibraryMovies、getLibrarySeries、getContentDetail 方法

- [x] 3. 前端新增组件
  - [x] 3.1 新增 SearchResultCard.tsx 搜索结果卡片组件
  - [x] 3.2 新增 MediaDetailSkeleton.tsx 详情页骨架屏组件
  - [x] 3.3 新增 ReviewCard.tsx 影评卡片组件

- [x] 4. 前端新增详情页
  - [x] 4.1 新增 MovieDetail.tsx 电影详情页（路由 /movie/:id）
  - [x] 4.2 新增 SeriesDetail.tsx 剧集详情页（路由 /series/:id）
  - [x] 4.3 更新 App.tsx 注册新路由

- [x] 5. 前端改造现有页面
  - [x] 5.1 重构 AddContent.tsx 为搜索式添加（防抖搜索+结果列表+预览面板）
  - [x] 5.2 改造 Movies.tsx 调用 library 接口，空状态引导
  - [x] 5.3 改造 Series.tsx 调用 library 接口，空状态引导
  - [x] 5.4 改造 Watchlist.tsx 卡片点击跳转详情页
