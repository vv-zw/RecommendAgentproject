# 需求文档

## 简介

本功能为"影视推荐系统"新增以下能力：

1. **搜索式添加影视**：将现有的手动填写表单改为从数据库实时搜索并选中影片，写入用户影片库（`user_preferences`）。
2. **电影页 / 剧集页展示用户影片库**：已登录用户看到的是自己明确添加的影片，而非基于偏好匹配的推荐内容；未登录时保持全量展示。
3. **影视详情页**：新增 `/movie/:id` 和 `/series/:id` 路由，展示影片完整信息，支持字段优雅降级，并提供"加入待看清单"和"加入我的影片库"操作。
4. **待看清单同步更新**：卡片支持点击跳转详情页，并展示封面图、片名、类型、评分、添加时间。

---

## 词汇表

- **Search_Bar**：添加影视页中的搜索输入框组件，用于输入片名和选择影片类型。
- **Search_Result_List**：搜索结果卡片列表组件，展示匹配的影片。
- **Search_Result_Card**：搜索结果列表中的单张卡片，显示封面图、片名、年份、类型标签、评分。
- **Preview_Panel**：用户选中影片后展示的完整预览区域（封面大图 + 基本信息）。
- **Content_Library**：用户通过"添加影视"功能写入 `user_preferences` 表的个人影片库。
- **Detail_Page**：影视详情页，路由为 `/movie/:id` 或 `/series/:id`。
- **Watchlist**：待看清单，存储于 `app.watchlists` 表。
- **Watchlist_Card**：待看清单页中的单张卡片。
- **System**：影视推荐系统前后端整体。
- **Backend**：Flask + PostgreSQL 后端服务。
- **Frontend**：React 18 + TypeScript + TailwindCSS 前端应用。
- **content_items**：`app.content_items` 数据库表，存储影视内容主数据。
- **user_preferences**：`app.user_preferences` 数据库表，存储用户个人影片库。
- **watchlists**：`app.watchlists` 数据库表，存储待看清单。

---

## 需求

### 需求 1：搜索式添加影视

**用户故事：** 作为已登录用户，我希望通过搜索片名来找到并添加影片到我的影片库，而不是手动填写所有字段，从而快速建立我的个人影片库。

#### 验收标准

1. THE Search_Bar SHALL 提供片名文本输入框和影片类型选择器（电影 / 剧集）。
2. WHEN 用户在 Search_Bar 中输入片名时，THE System SHALL 在用户停止输入 300ms 后向 `content_items` 表发起实时搜索请求。
3. WHEN 搜索请求返回结果时，THE Search_Result_List SHALL 以卡片列表形式展示匹配的影片，每张 Search_Result_Card 显示封面图、片名、年份、类型标签和评分。
4. WHEN 搜索结果为空时，THE Search_Result_List SHALL 展示"未找到匹配影片"的空状态提示。
5. WHEN 用户点击某张 Search_Result_Card 时，THE Preview_Panel SHALL 展示该影片的封面大图和基本信息（片名、年份、类型、评分、简介）。
6. WHEN 用户在 Preview_Panel 中点击"确认添加"按钮时，THE Backend SHALL 将该影片的 `content_id`、`content_type`、`title`、`genres`、`rating`、`year`、`director`、`actors`、`cover_url` 写入 `user_preferences` 表。
7. WHEN 影片成功写入 `user_preferences` 表后，THE Frontend SHALL 展示"已加入您的影片库"的成功提示。
8. IF 同一影片已存在于用户的 `user_preferences` 记录中，THEN THE Backend SHALL 返回幂等成功响应，THE Frontend SHALL 展示"该影片已在您的影片库中"的提示。
9. IF 用户未登录时访问添加影视页，THEN THE Frontend SHALL 展示登录引导提示，并提供跳转登录页的链接。
10. WHEN 用户选中影片后，THE Preview_Panel SHALL 提供"取消选择"操作，允许用户重新搜索。

---

### 需求 2：电影页展示用户影片库

**用户故事：** 作为已登录用户，我希望在电影页看到我明确添加的电影，而不是系统推荐的内容，从而管理我自己的电影收藏。

#### 验收标准

1. WHEN 已登录用户访问电影页时，THE Frontend SHALL 调用用户影片库接口，展示该用户 `user_preferences` 表中 `content_type='movie'` 的所有影片。
2. THE Frontend SHALL 在电影页每张卡片上展示封面图、片名和类型标签。
3. WHEN 已登录用户的 `user_preferences` 表中无电影记录时，THE Frontend SHALL 展示空状态提示，并提供跳转至添加影视页的引导链接。
4. WHEN 未登录用户访问电影页时，THE Frontend SHALL 调用全量电影接口，展示 `content_items` 表中的全量电影数据。
5. THE Backend SHALL 提供 `GET /api/users/{user_id}/library/movies` 接口，返回该用户 `user_preferences` 表中 `content_type='movie'` 的影片列表。

---

### 需求 3：剧集页展示用户影片库

**用户故事：** 作为已登录用户，我希望在剧集页看到我明确添加的剧集，而不是系统推荐的内容，从而管理我自己的剧集收藏。

#### 验收标准

1. WHEN 已登录用户访问剧集页时，THE Frontend SHALL 调用用户影片库接口，展示该用户 `user_preferences` 表中 `content_type='series'` 的所有剧集。
2. THE Frontend SHALL 在剧集页每张卡片上展示封面图、片名和类型标签。
3. WHEN 已登录用户的 `user_preferences` 表中无剧集记录时，THE Frontend SHALL 展示空状态提示，并提供跳转至添加影视页的引导链接。
4. WHEN 未登录用户访问剧集页时，THE Frontend SHALL 调用全量剧集接口，展示 `content_items` 表中的全量剧集数据。
5. THE Backend SHALL 提供 `GET /api/users/{user_id}/library/series` 接口，返回该用户 `user_preferences` 表中 `content_type='series'` 的剧集列表。

---

### 需求 4：影视详情页

**用户故事：** 作为用户，我希望点击任意影片后能查看其完整信息，从而了解影片详情并决定是否添加到待看清单或影片库。

#### 验收标准

1. THE System SHALL 提供 `/movie/:id` 和 `/series/:id` 两个路由，分别对应电影和剧集的详情页。
2. WHEN 用户访问详情页时，THE Detail_Page SHALL 展示以下字段（若字段存在）：封面大图、片名、原片名、评分、类型标签、上映年份、地区、语言、时长（电影）/ 集数（剧集）、导演、主演列表、剧情简介。
3. WHERE `reviews` 字段存在于数据记录中，THE Detail_Page SHALL 展示热门影评区块。
4. WHERE `cast` 字段存在于数据记录中，THE Detail_Page SHALL 展示完整演员表区块。
5. IF 某字段在数据记录中不存在或为空，THEN THE Detail_Page SHALL 不渲染该字段对应的 UI 区块，且不产生页面错误。
6. WHEN 已登录用户在详情页点击"加入待看清单"按钮时，THE Backend SHALL 将该影片写入 `watchlists` 表，THE Frontend SHALL 将按钮状态更新为"已加入待看"。
7. WHEN 已登录用户在详情页点击"加入我的影片库"按钮时，THE Backend SHALL 将该影片写入 `user_preferences` 表，THE Frontend SHALL 将按钮状态更新为"已在影片库"。
8. IF 用户未登录时点击"加入待看清单"或"加入我的影片库"按钮，THEN THE Frontend SHALL 展示登录引导提示。
9. WHEN 详情页数据加载中时，THE Detail_Page SHALL 展示加载骨架屏（Skeleton）。
10. IF 影片 ID 不存在或接口返回 404，THEN THE Detail_Page SHALL 展示"影片不存在"的错误提示，并提供返回上一页的链接。
11. THE Backend SHALL 提供 `GET /api/content/:id` 通用详情接口，返回 `content_items` 表中该 ID 对应记录的完整字段，包括 `raw_source` JSONB 中的扩展字段（如 `reviews`、`cast`）。

---

### 需求 5：待看清单同步更新

**用户故事：** 作为用户，我希望在待看清单中点击影片卡片能跳转到详情页，并能看到封面图、片名、类型、评分和添加时间，从而更方便地管理我的待看内容。

#### 验收标准

1. WHEN 用户点击待看清单中的 Watchlist_Card 时，THE Frontend SHALL 根据影片类型跳转至对应的 `/movie/:id` 或 `/series/:id` 详情页。
2. THE Watchlist_Card SHALL 展示封面图、片名、类型标签、评分和添加时间。
3. WHEN 封面图 URL 无效或加载失败时，THE Watchlist_Card SHALL 展示占位图，不产生页面错误。
4. THE Frontend SHALL 保留现有的"标记已看"和"移除"操作按钮。
