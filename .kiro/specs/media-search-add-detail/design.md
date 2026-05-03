# 技术设计文档：media-search-add-detail

## 概述

本功能在现有影视推荐系统基础上新增四项能力：

1. **搜索式添加影视**：将 AddContent 页面从手动填写表单改造为防抖搜索 + 结果预览 + 一键写入 `user_preferences` 的交互流程。
2. **电影页 / 剧集页展示用户影片库**：已登录用户看到自己明确添加的影片（`user_preferences`），未登录时保持全量展示。
3. **影视详情页**：新增 `/movie/:id` 和 `/series/:id` 路由，展示完整影片信息，支持 `raw_source` JSONB 扩展字段优雅降级。
4. **待看清单卡片跳转**：Watchlist 卡片点击跳转详情页，并展示封面图、片名、类型、评分、添加时间。

### 设计原则

- **最小侵入**：复用现有 `content_item_to_media()` 序列化函数、`token_required` 装饰器、Axios 实例和 Zustand store，不引入新的状态管理方案。
- **幂等写入**：`user_preferences` 表已有 `UNIQUE(user_id, content_id, content_type)` 约束，后端使用 `ON CONFLICT DO NOTHING` 实现幂等。
- **优雅降级**：前端详情页所有扩展字段（`reviews`、`cast` 等）均从 `raw_source` JSONB 中读取，字段不存在时不渲染对应区块。
- **防抖搜索**：复用现有 `GET /api/search` 接口，前端添加 300ms 防抖，避免频繁请求。

## 架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        React 前端                                │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  AddContent  │  │  Movies /    │  │  MovieDetail /       │  │
│  │  (重构)      │  │  Series      │  │  SeriesDetail (新增) │  │
│  │  搜索+预览   │  │  (改造)      │  │  详情+操作           │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│  ┌──────▼─────────────────▼──────────────────────▼───────────┐  │
│  │              content.ts API 层（Axios）                    │  │
│  │  searchMedia / addToLibrary / getLibraryMovies /           │  │
│  │  getLibrarySeries / getContentDetail                       │  │
│  └──────────────────────────┬──────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────┘
                              │ HTTP / JSON
┌─────────────────────────────▼───────────────────────────────────┐
│                     Flask 后端 (api/routes.py)                   │
│                                                                  │
│  GET  /api/search                  (已有，复用)                  │
│  POST /api/users/{id}/library      (新增)                        │
│  GET  /api/users/{id}/library/movies   (新增)                    │
│  GET  /api/users/{id}/library/series   (新增)                    │
│  GET  /api/content/{id}            (新增)                        │
│                                                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ psycopg3
┌─────────────────────────────▼───────────────────────────────────┐
│                     PostgreSQL (schema: app)                     │
│                                                                  │
│  app.content_items      (只读，搜索和详情查询)                   │
│  app.user_preferences   (读写，影片库)                           │
│  app.watchlists         (读写，待看清单)                         │
└─────────────────────────────────────────────────────────────────┘
```

### 数据流：搜索式添加影视

```
用户输入片名
    │ 300ms 防抖
    ▼
GET /api/search?query=xxx&media_type=movie|series
    │
    ▼
SearchResultList 展示卡片
    │ 用户点击卡片
    ▼
PreviewPanel 展示详情
    │ 用户点击"确认添加"
    ▼
POST /api/users/{id}/library
    │ ON CONFLICT DO NOTHING
    ▼
user_preferences 表写入
    │
    ▼
前端展示成功/已存在提示
```

### 数据流：详情页

```
用户点击卡片 / 直接访问 URL
    │
    ▼
React Router 匹配 /movie/:id 或 /series/:id
    │
    ▼
GET /api/content/{id}
    │ 返回完整字段 + raw_source JSONB
    ▼
DetailPage 渲染
    ├── 基础字段（title, rating, year, ...）
    ├── raw_source.reviews → ReviewCard（可选）
    └── raw_source.cast → 演员表（可选）
```

## 组件与接口

### 后端新增接口

#### 1. POST /api/users/{user_id}/library — 添加影片到用户影片库

**认证**：`@token_required`（需要 `x-access-token` Header）

**请求体**：
```json
{
  "content_id": "12345",
  "content_type": "movie",
  "title": "流浪地球",
  "genres": "科幻/冒险",
  "rating": 7.9,
  "year": 2019,
  "director": "郭帆",
  "actors": "吴京/屈楚萧",
  "cover_url": "https://..."
}
```

**响应**：
- `201 Created`：`{"message": "已加入您的影片库", "id": 1}`
- `200 OK`（幂等）：`{"message": "该影片已在您的影片库中", "id": 1}`
- `400 Bad Request`：缺少必填字段
- `403 Forbidden`：user_id 与 token 不匹配

**实现要点**：
- 使用 `INSERT INTO user_preferences ... ON CONFLICT (user_id, content_id, content_type) DO NOTHING RETURNING id`
- 若 `RETURNING id` 为空（冲突），查询已有记录的 id 并返回 200

---

#### 2. GET /api/users/{user_id}/library/movies — 获取用户电影库

**认证**：`@token_required`

**查询参数**：`page`（默认 1）、`limit`（默认 20）

**响应**：
```json
{
  "total": 5,
  "page": 1,
  "limit": 20,
  "results": [
    {
      "id": 1,
      "content_id": "12345",
      "title": "流浪地球",
      "cover_url": "...",
      "genres": "科幻/冒险",
      "rating": 7.9,
      "year": 2019,
      "media_type": "movie",
      "added_at": "2024-01-01T00:00:00"
    }
  ]
}
```

**实现要点**：
- 查询 `user_preferences WHERE user_id = %s AND content_type = 'movie'`
- 按 `created_at DESC` 排序
- 返回字段映射为前端 `MediaItem` 格式（`cover_url` → `poster_path`，`rating` → `vote_average`）

---

#### 3. GET /api/users/{user_id}/library/series — 获取用户剧集库

与 `/library/movies` 完全对称，`content_type = 'series'`。

---

#### 4. GET /api/content/{id} — 通用详情接口

**认证**：无需认证（公开接口）

**路径参数**：`id`（`content_items.id`，BIGINT）

**响应**：
```json
{
  "id": 12345,
  "title": "流浪地球",
  "original_title": "The Wandering Earth",
  "overview": "...",
  "poster_path": "...",
  "vote_average": 7.9,
  "media_type": "movie",
  "genres": ["科幻", "冒险"],
  "year": 2019,
  "region": "中国",
  "language": "普通话",
  "duration": "125分钟",
  "director": "郭帆",
  "actors": "吴京/屈楚萧",
  "raw_source": {
    "reviews": [...],
    "cast": [...],
    "awards": [...]
  }
}
```

**实现要点**：
- 查询 `content_items WHERE id = %s`
- 使用扩展版序列化函数 `content_item_to_media_detail(row)`，在 `content_item_to_media()` 基础上额外包含 `raw_source` 字段
- `raw_source` 为 `None` 时返回 `{}`，不返回 `null`

---

### 前端新增 / 改造组件

#### 新增：SearchResultCard.tsx

```
props:
  item: MediaItem
  isSelected: boolean
  onClick: (item: MediaItem) => void

渲染：
  - 封面图（poster_path，失败时占位图）
  - 片名（title）
  - 年份（release_date）
  - 类型标签（media_type）
  - 评分（vote_average，> 0 时显示）
  - 选中状态高亮边框
```

#### 新增：MediaDetailSkeleton.tsx

骨架屏组件，模拟详情页布局：
- 左侧封面图占位（灰色矩形，animate-pulse）
- 右侧标题、评分、标签、简介占位行

#### 新增：ReviewCard.tsx（可选渲染）

```
props:
  review: { author: string; content: string; rating?: number; date?: string }

渲染：
  - 作者名
  - 评分（可选）
  - 评论内容（line-clamp-4）
  - 日期（可选）
```

#### 新增：MovieDetail.tsx（路由 /movie/:id）

状态：
- `detail: ContentDetail | null`
- `loading: boolean`
- `error: string | null`
- `inWatchlist: boolean`
- `inLibrary: boolean`

生命周期：
1. `useEffect` 监听 `id` 参数，调用 `GET /api/content/{id}`
2. 已登录时并发查询 watchlist 状态

渲染逻辑：
- loading → `<MediaDetailSkeleton />`
- error / 404 → 错误提示 + 返回链接
- 正常 → 详情布局（见下方）

#### 新增：SeriesDetail.tsx（路由 /series/:id）

与 MovieDetail.tsx 结构相同，差异：
- 展示"集数"（episodes）而非"时长"（duration）
- 页面标题标注"剧集"

#### 改造：AddContent.tsx

**改造前**：手动填写表单，调用 `POST /api/content/add`（写入 content_items）

**改造后**：
1. 搜索区：片名输入框 + 类型选择器（电影/剧集）
2. 搜索结果区：`SearchResultCard` 列表（防抖 300ms 触发）
3. 预览区：选中影片后展示 `PreviewPanel`（封面大图 + 基本信息 + 确认/取消按钮）
4. 未登录时展示登录引导，不渲染搜索区

**调用接口**：
- 搜索：`GET /api/search?query=xxx&media_type=xxx`（已有）
- 添加：`POST /api/users/{id}/library`（新增）

#### 改造：Movies.tsx

- 已登录时调用 `GET /api/users/{id}/library/movies` 替代 `getPreferenceMovies`
- 空状态时展示引导链接（跳转 `/add-content`）
- 移除 `isFallback` 逻辑（影片库为空即空状态，不再兜底全量）

#### 改造：Series.tsx

与 Movies.tsx 改造对称，调用 `GET /api/users/{id}/library/series`。

#### 改造：Watchlist.tsx

- 卡片整体可点击，`onClick` 根据 `media_type` 跳转 `/movie/:id` 或 `/series/:id`
- 卡片展示字段：封面图、片名、类型标签、评分、添加时间
- 保留"标记已看"和"移除"按钮

#### 改造：App.tsx

新增路由：
```tsx
<Route path="/movie/:id" element={<MovieDetail />} />
<Route path="/series/:id" element={<SeriesDetail />} />
```

#### 改造：frontend/src/api/content.ts

新增 API 方法：
```typescript
// 添加到用户影片库
addToLibrary(userId: number, data: LibraryAddRequest): Promise<LibraryAddResponse>

// 获取用户电影库
getLibraryMovies(userId: number, params?: PaginationParams): Promise<MediaListResponse>

// 获取用户剧集库
getLibrarySeries(userId: number, params?: PaginationParams): Promise<MediaListResponse>

// 获取通用详情（含 raw_source）
getContentDetail(id: number): Promise<ContentDetail>
```

新增类型：
```typescript
interface LibraryAddRequest {
  content_id: string;
  content_type: 'movie' | 'series';
  title: string;
  genres?: string;
  rating?: number;
  year?: number;
  director?: string;
  actors?: string;
  cover_url?: string;
}

interface ContentDetail extends MediaItem {
  original_title?: string;
  episodes?: string;
  raw_source?: {
    reviews?: ReviewItem[];
    cast?: CastMember[];
    awards?: string[];
    [key: string]: unknown;
  };
}

interface ReviewItem {
  author: string;
  content: string;
  rating?: number;
  date?: string;
}

interface CastMember {
  name: string;
  role?: string;
  avatar?: string;
}
```

## 数据模型

### 现有表结构（只读参考）

#### app.content_items（搜索和详情查询来源）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| source_item_id | VARCHAR(64) | 外部来源 ID |
| content_type | VARCHAR(16) | 'movie' 或 'series' |
| title | VARCHAR(255) | 中文片名 |
| original_title | VARCHAR(255) | 原片名 |
| genres | TEXT | 类型，如 "科幻/冒险" |
| rating | NUMERIC(3,1) | 评分 |
| year | INTEGER | 上映年份 |
| director | VARCHAR(255) | 导演 |
| actors | TEXT | 主演，如 "吴京/屈楚萧" |
| cover_url | TEXT | 封面图 URL |
| plot | TEXT | 剧情简介 |
| popularity | NUMERIC(10,4) | 热度 |
| region | VARCHAR(100) | 地区 |
| language | VARCHAR(100) | 语言 |
| duration | VARCHAR(100) | 时长（电影） |
| episodes | VARCHAR(100) | 集数（剧集） |
| status | VARCHAR(100) | 状态 |
| raw_source | JSONB | 扩展字段（reviews、cast 等） |

#### app.user_preferences（用户影片库）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| user_id | VARCHAR(64) | 用户 ID |
| content_id | VARCHAR(64) | 对应 content_items.id（字符串形式） |
| content_type | VARCHAR(16) | 'movie' 或 'series' |
| title | VARCHAR(255) | 片名（冗余存储，避免 JOIN） |
| genres | TEXT | 类型 |
| rating | NUMERIC(3,1) | 评分 |
| year | INTEGER | 年份 |
| director | VARCHAR(255) | 导演 |
| actors | TEXT | 主演 |
| cover_url | TEXT | 封面图 URL |
| comment | TEXT | 用户备注（可选） |
| source | VARCHAR(64) | 来源标识 |
| created_at | TIMESTAMP | 添加时间 |
| updated_at | TIMESTAMP | 更新时间 |

**唯一约束**：`UNIQUE(user_id, content_id, content_type)`

### 前端数据模型

#### ContentDetail（详情页数据）

```typescript
interface ContentDetail {
  // 基础字段（来自 content_item_to_media）
  id: number;
  title: string;
  overview: string;           // 映射自 plot
  poster_path: string;        // 映射自 cover_url
  backdrop_path: string;      // 同 cover_url
  release_date: string;       // 映射自 year
  vote_average: number;       // 映射自 rating
  media_type: 'movie' | 'series';
  genres: string[];           // 解析自 genres 字符串
  director: string;
  actors: string;
  region: string;
  language: string;
  duration: string;           // 电影时长
  // 详情页扩展字段
  original_title?: string;
  episodes?: string;          // 剧集集数
  raw_source?: {
    reviews?: ReviewItem[];
    cast?: CastMember[];
    awards?: string[];
    [key: string]: unknown;   // 未来扩展字段
  };
}
```

#### LibraryItem（影片库列表项）

```typescript
interface LibraryItem {
  id: number;           // user_preferences.id
  content_id: string;   // 对应 content_items.id
  title: string;
  cover_url: string;
  genres: string;
  rating: number;
  year: number;
  media_type: 'movie' | 'series';
  added_at: string;     // created_at ISO 字符串
  // 映射为 MediaItem 格式供 MovieCard 复用
  poster_path: string;  // = cover_url
  vote_average: number; // = rating
  overview: string;     // 空字符串（影片库不存 plot）
}
```

### 后端序列化函数扩展

新增 `content_item_to_media_detail(row)` 函数，在现有 `content_item_to_media()` 基础上追加：

```python
def content_item_to_media_detail(row: dict) -> dict:
    base = content_item_to_media(row)
    base['original_title'] = row.get('original_title', '') or ''
    base['episodes'] = row.get('episodes', '') or ''
    base['raw_source'] = row.get('raw_source') or {}
    return base
```

`user_preferences` 行转 `MediaItem` 的辅助函数 `preference_to_media(row)`：

```python
def preference_to_media(row: dict) -> dict:
    genres_raw = row.get('genres') or ''
    genres_list = [g.strip() for g in genres_raw.split('/') if g.strip()]
    return {
        'id': row.get('id'),
        'content_id': str(row.get('content_id', '')),
        'title': row.get('title', ''),
        'overview': '',
        'poster_path': row.get('cover_url', '') or '',
        'backdrop_path': row.get('cover_url', '') or '',
        'release_date': str(row.get('year', '')) if row.get('year') else '',
        'vote_average': float(row.get('rating', 0) or 0),
        'vote_count': 0,
        'media_type': row.get('content_type', 'movie'),
        'genres': genres_list,
        'popularity': 0,
        'director': row.get('director', '') or '',
        'actors': row.get('actors', '') or '',
        'region': '',
        'language': '',
        'duration': '',
        'added_at': row.get('created_at').isoformat() if row.get('created_at') else '',
    }
```

## 正确性属性

*属性是在系统所有有效执行中都应成立的特征或行为——本质上是对系统应该做什么的形式化陈述。属性是人类可读规范与机器可验证正确性保证之间的桥梁。*

### 属性 1：防抖搜索只触发一次

*对任意* 输入字符串序列，当用户在 300ms 内连续输入多个字符时，搜索函数应只被调用一次（最后一次输入停止后 300ms 触发）。

**验证：需求 1.2**

---

### 属性 2：搜索结果卡片包含必要字段

*对任意* 非空搜索结果列表，渲染 SearchResultCard 后，每张卡片应包含封面图（或占位图）、片名、年份、类型标签和评分（评分 > 0 时显示）。

**验证：需求 1.3**

---

### 属性 3：影片库写入 round-trip

*对任意* 合法影片数据（包含 content_id、content_type、title），调用 `POST /api/users/{id}/library` 写入后，再调用 `GET /api/users/{id}/library/{movies|series}` 查询，返回列表中应包含该影片的 title 和 content_id。

**验证：需求 1.6、4.7**

---

### 属性 4：影片库写入幂等性

*对任意* 合法影片数据，连续调用两次 `POST /api/users/{id}/library`，两次均应返回成功状态码（201 或 200），且 `GET /api/users/{id}/library/{type}` 中该影片只出现一次。

**验证：需求 1.8**

---

### 属性 5：影片库接口类型过滤正确性

*对任意* 用户 ID，`GET /api/users/{id}/library/movies` 返回的所有记录的 `media_type` 均为 `'movie'`；`GET /api/users/{id}/library/series` 返回的所有记录的 `media_type` 均为 `'series'`。

**验证：需求 2.5、3.5**

---

### 属性 6：详情页渲染所有存在字段

*对任意* 包含完整字段的影片数据（title、rating、year、region、language、duration、director、actors、overview），渲染 MovieDetail / SeriesDetail 后，所有非空字段对应的 UI 区块均应出现在渲染结果中。

**验证：需求 4.2**

---

### 属性 7：raw_source 扩展字段条件渲染

*对任意* 影片数据，若 `raw_source.reviews` 数组非空，则渲染详情页后影评区块应存在；若 `raw_source.cast` 数组非空，则演员表区块应存在。反之，若对应字段为空或不存在，则对应区块不应出现在渲染结果中，且组件不产生错误。

**验证：需求 4.3、4.4、4.5**

---

### 属性 8：待看清单写入 round-trip

*对任意* 存在的影片 ID，已登录用户调用"加入待看清单"后，`GET /api/users/{id}/watchlist` 返回的列表中应包含该影片 ID。

**验证：需求 4.6**

---

### 属性 9：通用详情接口返回 raw_source 字段

*对任意* 存在于 `content_items` 表中的影片 ID，`GET /api/content/{id}` 的响应体中应包含 `raw_source` 键（值可为空对象 `{}`，但键必须存在）。

**验证：需求 4.11**

---

### 属性 10：Watchlist 卡片跳转路径正确性

*对任意* `media_type` 为 `'movie'` 或 `'series'` 的待看清单项，点击卡片后跳转的路径应分别为 `/movie/{id}` 或 `/series/{id}`，其中 `{id}` 与该项的 `id` 字段一致。

**验证：需求 5.1**

---

### 属性 11：Watchlist 卡片渲染必要字段

*对任意* 待看清单项数据，渲染 Watchlist_Card 后，应包含封面图（或占位图）、片名、类型标签、评分（> 0 时显示）和添加时间。

**验证：需求 5.2**

## 错误处理

### 后端错误处理

| 场景 | HTTP 状态码 | 响应体 |
|------|------------|--------|
| 缺少必填字段（content_id、content_type、title） | 400 | `{"error": "Missing required fields"}` |
| user_id 与 token 不匹配 | 403 | `{"error": "Unauthorized"}` |
| content_id 不存在于 content_items（宽松，不强制校验） | 201 | 正常写入（允许离线添加） |
| 影片 ID 不存在（/api/content/{id}） | 404 | `{"error": "Content not found"}` |
| 数据库连接失败 | 500 | `{"error": "Internal server error", "detail": "..."}` |
| Token 过期 | 401 | `{"message": "Token has expired!"}` |

**幂等处理逻辑**（POST /api/users/{id}/library）：

```python
# 使用 ON CONFLICT DO NOTHING + RETURNING id
cur.execute("""
    INSERT INTO {SCHEMA}.user_preferences
        (user_id, content_id, content_type, title, genres, rating, year,
         director, actors, cover_url, source)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'search')
    ON CONFLICT (user_id, content_id, content_type) DO NOTHING
    RETURNING id
""", (...))
row = cur.fetchone()
if row:
    return jsonify({"message": "已加入您的影片库", "id": row['id']}), 201
else:
    # 冲突，查询已有记录
    cur.execute("SELECT id FROM ... WHERE user_id=%s AND content_id=%s AND content_type=%s", ...)
    existing = cur.fetchone()
    return jsonify({"message": "该影片已在您的影片库中", "id": existing['id']}), 200
```

### 前端错误处理

#### AddContent 页面

- 搜索请求失败：展示"搜索失败，请稍后重试"提示，不清空已有结果
- 添加请求失败：展示错误提示（来自后端 `error` 字段），保留预览面板
- 未登录：渲染登录引导，不渲染搜索区

#### 详情页（MovieDetail / SeriesDetail）

- 加载中：展示 `<MediaDetailSkeleton />`
- 404 / 接口错误：展示"影片不存在"提示 + 返回上一页链接
- 封面图加载失败：`onError` 替换为占位图（灰色背景 + 图标）
- 操作按钮（加入待看 / 加入影片库）失败：Toast 提示，按钮恢复可点击状态

#### Watchlist 页面

- 封面图加载失败：`onError` 替换为占位图（已有实现，保留）
- 移除失败：乐观更新回滚（已有实现，保留）

#### Movies / Series 页面

- 影片库接口失败：展示错误提示 + 重试按钮
- 空状态：展示"您的影片库暂无内容"+ 跳转添加影视页的引导链接

### 图片加载失败统一处理

所有封面图使用统一的 `onError` 处理器：

```tsx
const handleImageError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  e.currentTarget.src = '/placeholder-poster.jpg';
};
```

若 `poster_path` 为空字符串，直接渲染占位图，不发起无效请求。

## 测试策略

### 双轨测试方法

本功能同时采用**单元测试**和**属性测试**：

- **单元测试**：验证具体场景、边界条件和错误状态（EXAMPLE / EDGE_CASE 类条目）
- **属性测试**：验证跨输入的通用属性（PROPERTY 类条目）

### 属性测试配置

**前端**：使用 [fast-check](https://github.com/dubzzz/fast-check)（TypeScript 属性测试库）

```bash
npm install --save-dev fast-check
```

每个属性测试最少运行 **100 次迭代**。

**后端**：使用 [Hypothesis](https://hypothesis.readthedocs.io/)（Python 属性测试库）

```bash
pip install hypothesis
```

### 属性测试实现指引

每个属性测试需在注释中标注对应的设计属性：

```typescript
// Feature: media-search-add-detail, Property 2: 搜索结果卡片包含必要字段
it('SearchResultCard renders required fields for any media item', () => {
  fc.assert(
    fc.property(
      fc.record({
        id: fc.integer({ min: 1 }),
        title: fc.string({ minLength: 1 }),
        poster_path: fc.string(),
        release_date: fc.string(),
        vote_average: fc.float({ min: 0, max: 10 }),
        media_type: fc.constantFrom('movie', 'series'),
        genres: fc.array(fc.string()),
        // ...
      }),
      (item) => {
        const { getByText } = render(<SearchResultCard item={item} ... />);
        expect(getByText(item.title)).toBeInTheDocument();
        // 验证其他必要字段...
      }
    ),
    { numRuns: 100 }
  );
});
```

```python
# Feature: media-search-add-detail, Property 4: 影片库写入幂等性
@given(
    content_id=st.text(min_size=1, max_size=64),
    title=st.text(min_size=1, max_size=255),
    content_type=st.sampled_from(['movie', 'series']),
)
@settings(max_examples=100)
def test_library_add_idempotent(content_id, title, content_type):
    # 连续调用两次，验证只有一条记录
    ...
```

### 单元测试覆盖点

| 测试场景 | 类型 | 对应需求 |
|---------|------|---------|
| AddContent 渲染搜索框和类型选择器 | EXAMPLE | 1.1 |
| 搜索结果为空时展示空状态提示 | EXAMPLE | 1.4 |
| 添加成功后展示成功提示 | EXAMPLE | 1.7 |
| 未登录时展示登录引导 | EXAMPLE | 1.9、4.8 |
| 选中影片后展示取消按钮 | EXAMPLE | 1.10 |
| 已登录时调用 library 接口 | EXAMPLE | 2.1 |
| 未登录时调用全量接口 | EXAMPLE | 2.4 |
| 影片库为空时展示引导链接 | EXAMPLE | 2.3、3.3 |
| 路由 /movie/:id 和 /series/:id 存在 | EXAMPLE | 4.1 |
| 加载中展示骨架屏 | EXAMPLE | 4.9 |
| 404 时展示错误提示 | EXAMPLE | 4.10 |
| 封面图加载失败展示占位图 | EDGE_CASE | 5.3 |
| 保留"标记已看"和"移除"按钮 | EXAMPLE | 5.4 |

### 集成测试

后端接口集成测试（使用 pytest + 测试数据库）：

1. `POST /api/users/{id}/library` → 验证数据库写入
2. `GET /api/users/{id}/library/movies` → 验证只返回 movie 类型
3. `GET /api/users/{id}/library/series` → 验证只返回 series 类型
4. `GET /api/content/{id}` → 验证返回 raw_source 字段
5. 幂等性：重复 POST 不产生重复记录

### 测试文件结构

```
frontend/src/
  __tests__/
    components/
      SearchResultCard.test.tsx    # 属性 2
      MediaDetailSkeleton.test.tsx # 单元测试
      ReviewCard.test.tsx          # 单元测试
    pages/
      AddContent.test.tsx          # 属性 1、单元测试
      MovieDetail.test.tsx         # 属性 6、7、单元测试
      Movies.test.tsx              # 属性 5（前端侧）、单元测试
      Watchlist.test.tsx           # 属性 10、11、单元测试

tests/
  test_library_api.py              # 属性 3、4、5（后端侧）
  test_content_detail_api.py       # 属性 8、9
```
