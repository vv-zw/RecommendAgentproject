# 需求文档

## 简介

本功能将影视推荐系统的四个核心页面从展示全量数据升级为基于用户偏好的个性化展示。具体包括：电影页和剧集页根据 `user_preferences` 表中的用户偏好记录筛选内容；待看清单页从模拟数据切换为读取 `watchlists` 表的真实数据；AI Agent 助手页的快捷推荐词条和对话上下文均基于用户偏好动态生成，使推荐结果更加个性化。

## 词汇表

- **System**：影视推荐系统整体，包含后端 Flask API 和前端 React 应用
- **Movies_Page**：前端电影页（`Movies.tsx`），展示电影内容的页面
- **Series_Page**：前端剧集页（`Series.tsx`），展示剧集内容的页面
- **Watchlist_Page**：前端待看清单页（`Watchlist.tsx`），展示用户待看内容的页面
- **Agent_Page**：前端 AI 助手页（`AgentAssistant.tsx`），提供智能推荐对话的页面
- **API_Server**：后端 Flask API 服务（`api/routes.py`）
- **Agent_Module**：后端 AI Agent 模块（`agent/`），负责处理推荐对话请求
- **Authenticated_User**：已通过 JWT 认证的登录用户
- **user_preferences**：数据库中存储用户偏好的表，字段包括 `user_id`、`content_id`、`content_type`、`title`、`genres`、`rating`、`year`、`director`、`actors`
- **watchlists**：数据库中存储用户待看清单的表，字段包括 `id`、`user_id`、`media_id`、`added_at`
- **content_items**：数据库中存储影视内容的表，字段包括 `id`、`title`、`content_type`、`genres`、`rating`、`year`、`plot`、`cover_url`、`popularity`
- **Preference_Movies_API**：新增的后端接口，返回基于用户偏好筛选的电影列表
- **Preference_Series_API**：新增的后端接口，返回基于用户偏好筛选的剧集列表
- **User_Preferences_API**：新增的后端接口，返回当前用户的偏好数据
- **Quick_Prompts**：AI 助手页中的快捷提示按钮，供用户一键发起推荐请求

---

## 需求

### 需求 1：电影页展示用户偏好相关电影

**用户故事：** 作为已登录用户，我希望电影页只展示与我偏好相关的电影，以便快速找到符合我口味的内容，而不是浏览全部电影。

#### 验收标准

1. WHEN 已认证用户访问电影页，THE Movies_Page SHALL 调用基于用户偏好的电影列表接口，而非全量电影接口
2. WHEN API_Server 收到已认证用户的偏好电影请求，THE Preference_Movies_API SHALL 查询 `user_preferences` 表中该用户 `content_type = 'movie'` 的偏好记录，并关联 `content_items` 表返回对应电影列表
3. WHEN 用户的 `user_preferences` 表中存在电影偏好记录，THE Preference_Movies_API SHALL 返回与这些偏好记录中 `genres`、`director`、`actors` 字段相匹配的 `content_items` 电影，按 `popularity` 降序排列
4. WHEN 用户的 `user_preferences` 表中不存在任何电影偏好记录，THE Preference_Movies_API SHALL 返回全量电影列表作为兜底，并在响应中包含 `is_fallback: true` 标识
5. WHEN 用户未登录访问电影页，THE Movies_Page SHALL 调用全量电影列表接口，展示所有电影
6. IF Preference_Movies_API 查询失败，THEN THE API_Server SHALL 返回 HTTP 500 状态码及描述性错误信息
7. THE Preference_Movies_API SHALL 支持 `page`、`limit`、`genre`、`sort_by` 查询参数，与现有电影接口保持一致

### 需求 2：剧集页展示用户偏好相关剧集

**用户故事：** 作为已登录用户，我希望剧集页只展示与我偏好相关的剧集，以便快速找到符合我口味的剧集内容。

#### 验收标准

1. WHEN 已认证用户访问剧集页，THE Series_Page SHALL 调用基于用户偏好的剧集列表接口，而非全量剧集接口
2. WHEN API_Server 收到已认证用户的偏好剧集请求，THE Preference_Series_API SHALL 查询 `user_preferences` 表中该用户 `content_type = 'series'` 的偏好记录，并关联 `content_items` 表返回对应剧集列表
3. WHEN 用户的 `user_preferences` 表中存在剧集偏好记录，THE Preference_Series_API SHALL 返回与这些偏好记录中 `genres`、`director`、`actors` 字段相匹配的 `content_items` 剧集，按 `popularity` 降序排列
4. WHEN 用户的 `user_preferences` 表中不存在任何剧集偏好记录，THE Preference_Series_API SHALL 返回全量剧集列表作为兜底，并在响应中包含 `is_fallback: true` 标识
5. WHEN 用户未登录访问剧集页，THE Series_Page SHALL 调用全量剧集列表接口，展示所有剧集
6. IF Preference_Series_API 查询失败，THEN THE API_Server SHALL 返回 HTTP 500 状态码及描述性错误信息
7. THE Preference_Series_API SHALL 支持 `page`、`limit`、`genre`、`sort_by` 查询参数，与现有剧集接口保持一致

### 需求 3：待看清单页展示数据库真实数据

**用户故事：** 作为已登录用户，我希望待看清单页展示我在数据库中真实保存的待看内容，而不是模拟数据，以便准确管理我的观看计划。

#### 验收标准

1. WHEN 已认证用户访问待看清单页，THE Watchlist_Page SHALL 调用 `/api/users/{user_id}/watchlist` 接口获取真实数据，替换现有的模拟数据
2. WHEN API_Server 收到待看清单请求，THE API_Server SHALL 联表查询 `watchlists` 和 `content_items`，返回包含完整影视信息（`title`、`plot`、`cover_url`、`rating`、`content_type`、`added_at`）的列表
3. WHEN 待看清单数据加载中，THE Watchlist_Page SHALL 展示加载状态指示器
4. WHEN 待看清单为空，THE Watchlist_Page SHALL 展示空状态提示，并提供跳转到电影页和剧集页的导航链接
5. WHEN 用户点击"移除"按钮，THE Watchlist_Page SHALL 调用 DELETE `/api/users/{user_id}/watchlist/{media_id}` 接口，并在成功后从页面列表中移除该条目，无需刷新整页
6. WHEN 用户未登录访问待看清单页，THE Watchlist_Page SHALL 展示提示信息，引导用户登录
7. IF 待看清单接口请求失败，THEN THE Watchlist_Page SHALL 展示错误提示信息，说明数据加载失败

### 需求 4：AI Agent 助手基于用户偏好生成个性化快捷词条

**用户故事：** 作为已登录用户，我希望 AI 助手页的快捷推荐词条根据我的偏好数据动态生成，并且 AI 在回答时能结合我的偏好给出更个性化的推荐。

#### 验收标准

1. WHEN 已认证用户访问 AI 助手页，THE Agent_Page SHALL 调用用户偏好接口获取当前用户的偏好数据，并基于偏好数据动态生成 Quick_Prompts
2. WHEN 用户偏好数据包含 `genres` 字段，THE Agent_Page SHALL 生成至少 1 条基于该类型的快捷推荐词条（例如："推荐更多[类型]电影"）
3. WHEN 用户偏好数据包含 `director` 字段，THE Agent_Page SHALL 生成至少 1 条基于该导演的快捷推荐词条（例如："推荐[导演]的其他作品"）
4. WHEN 用户偏好数据包含 `actors` 字段，THE Agent_Page SHALL 生成至少 1 条基于该演员的快捷推荐词条（例如："推荐[演员]主演的其他影视"）
5. WHEN 用户偏好数据为空或接口请求失败，THE Agent_Page SHALL 展示默认的静态快捷词条，不影响页面正常使用
6. WHEN 已认证用户发送对话消息，THE API_Server SHALL 在调用 Agent_Module 时将该用户的 `user_preferences` 数据作为上下文传入
7. WHEN Agent_Module 收到包含用户偏好上下文的请求，THE Agent_Module SHALL 优先推荐与用户偏好的 `genres`、`director`、`actors` 相关的内容
8. THE User_Preferences_API SHALL 提供 GET `/api/users/{user_id}/preferences` 接口，返回该用户在 `user_preferences` 表中的所有偏好记录
9. IF User_Preferences_API 查询失败，THEN THE API_Server SHALL 返回 HTTP 500 状态码及描述性错误信息
