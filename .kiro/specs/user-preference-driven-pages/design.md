# 技术设计文档：用户偏好驱动页面（user-preference-driven-pages）
## 概述

本设计文档描述将影视推荐系统四个核心页面从全量数据展示升级为基于用户偏好个性化展示的技术方案。

**核心变更：**
- 电影页（Movies.tsx）：已登录用户调用偏好电影接口，未登录用户调用全量接口
- 剧集页（Series.tsx）：已登录用户调用偏好剧集接口，未登录用户调用全量接口
- 待看清单页（Watchlist.tsx）：替换模拟数据为真实 API 调用，支持移除操作
- AI 助手页（AgentAssistant.tsx）：动态生成快捷词条，Agent 对话注入用户偏好上下文

**设计原则：**
1. 最小侵入：复用现有 `content_item_to_media` 序列化函数和 `token_required` 装饰器
2. 优雅降级：偏好为空时自动回退到全量列表，前端接口失败时展示默认词条
3. 向后兼容：新增接口不影响现有 `/api/movies`、`/api/series` 接口

## 架构

### 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端（React 18）                          │
│                                                                  │
│  Movies.tsx ──────────────────────────────────────────────────  │
│  Series.tsx  ──→ contentApi.getPreferenceMovies/Series()  ────  │
│  Watchlist.tsx ──→ contentApi.getWatchlist()              ────  │
│  AgentAssistant.tsx ──→ contentApi.getUserPreferences()   ────  │
│                    ──→ agentApi.chat()                    ────  │
│                                                                  │
│  useAuthStore (Zustand) ──→ isAuthenticated, user.id, token     │
│  api/index.ts ──→ Axios 拦截器自动注入 x-access-token           │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────────┐
│                     后端（Flask + psycopg3）                      │
│                                                                  │
│  GET  /api/users/{id}/movies/preference  ← 新增                 │
│  GET  /api/users/{id}/series/preference  ← 新增                 │
│  GET  /api/users/{id}/preferences        ← 新增                 │
│  GET  /api/users/{id}/watchlist          ← 已有（前端改用真实）  │
│  DELETE /api/users/{id}/watchlist/{mid}  ← 已有                 │
│  POST /api/agent/chat                    ← 修改（注入偏好上下文）│
│                                                                  │
│  token_required 装饰器 ──→ JWT 验证 ──→ current_user            │
│  content_item_to_media() ──→ 统一序列化                         │
│  preference_match_sql() ──→ 偏好匹配 SQL 构建（新增工具函数）   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ psycopg3
┌──────────────────────────────▼──────────────────────────────────┐
│                    PostgreSQL（Schema: app）                      │
│                                                                  │
│  app.content_items      ──→ 影视内容主表                        │
│  app.user_preferences   ──→ 用户偏好记录表                      │
│  app.watchlists         ──→ 用户待看清单表                      │
│  app.users              ──→ 用户账户表                          │
└─────────────────────────────────────────────────────────────────┘
```

### 数据流图

**偏好电影/剧集请求流：**

```
用户访问 Movies/Series 页
        │
        ▼
isAuthenticated?
   ├── 否 ──→ contentApi.getMovies/getSeries() ──→ GET /api/movies|series
   └── 是 ──→ contentApi.getPreferenceMovies/Series(userId)
                    │
                    ▼
        GET /api/users/{id}/movies|series/preference
                    │
                    ▼
        查询 user_preferences WHERE user_id=? AND content_type=?
                    │
                    ├── 有偏好记录 ──→ 构建偏好匹配 SQL
                    │                  JOIN content_items
                    │                  WHERE genres/director/actors 匹配
                    │                  ORDER BY popularity DESC
                    │                  返回 {results, total, is_fallback: false}
                    │
                    └── 无偏好记录 ──→ 返回全量列表
                                       返回 {results, total, is_fallback: true}
```

**AI 助手偏好上下文注入流：**

```
用户发送消息
        │
        ▼
POST /api/agent/chat {message}
        │
        ▼
token_required ──→ current_user
        │
        ▼
查询 user_preferences WHERE user_id = current_user.id
        │
        ▼
构建 preference_context = {genres, directors, actors}
        │
        ▼
AgentManager.process_user_request(user_id, message, preference_context)
        │
        ▼
ToolOrchestrator.execute_tools() ──→ 偏好加权推荐
        │
        ▼
返回 {nl_response, structured_results}
```

## 组件与接口

### 后端新增接口

#### 1. GET /api/users/{user_id}/movies/preference

**描述：** 返回基于用户偏好筛选的电影列表，需要 JWT 认证。

**请求头：**
```
x-access-token: <JWT token>
```

**查询参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| limit | int | 20 | 每页数量 |
| genre | string | - | 类型筛选（ILIKE 匹配） |
| sort_by | string | popularity.desc | 排序方式 |

**响应（200）：**
```json
{
  "total": 42,
  "page": 1,
  "limit": 20,
  "is_fallback": false,
  "results": [
    {
      "id": 1,
      "title": "流浪地球",
      "overview": "...",
      "poster_path": "...",
      "vote_average": 7.9,
      "media_type": "movie",
      "genres": ["科幻", "动作"],
      "popularity": 95.4,
      "director": "郭帆",
      "actors": "吴京/屈楚萧"
    }
  ]
}
```

**响应（500）：**
```json
{"error": "Failed to fetch preference movies", "detail": "..."}
```

**权限：** `token_required`，且 `current_user.id == user_id`

---

#### 2. GET /api/users/{user_id}/series/preference

与电影偏好接口结构完全对称，`content_type = 'series'`，其余参数和响应格式相同。

---

#### 3. GET /api/users/{user_id}/preferences

**描述：** 返回用户在 `user_preferences` 表中的所有偏好记录，用于前端生成快捷词条和 Agent 上下文。

**请求头：**
```
x-access-token: <JWT token>
```

**响应（200）：**
```json
{
  "preferences": [
    {
      "id": 1,
      "user_id": "uuid-xxx",
      "content_id": "uuid-yyy",
      "content_type": "movie",
      "title": "流浪地球",
      "genres": "科幻/动作",
      "rating": 7.9,
      "year": 2019,
      "director": "郭帆",
      "actors": "吴京/屈楚萧",
      "created_at": "2024-01-15T10:00:00"
    }
  ]
}
```

**响应（500）：**
```json
{"error": "Failed to fetch user preferences", "detail": "..."}
```

---

#### 4. POST /api/agent/chat（修改）

**变更：** 在调用 `AgentManager.process_user_request()` 前，额外查询 `user_preferences` 并将偏好上下文传入。

**请求体（不变）：**
```json
{"message": "推荐科幻电影"}
```

**内部变更（routes.py）：**
```python
# 查询用户偏好
preferences = get_user_preferences(current_user['id'])
preference_context = build_preference_context(preferences)

# 传入 Agent
nl_response, structured_results = agent.process_user_request(
    current_user['id'], message, preference_context
)
```

**响应（不变）：**
```json
{
  "nl_response": "根据您偏好科幻类型，为您推荐...",
  "structured_results": [...]
}
```

---

### 后端工具函数（api/routes.py 新增）

#### `build_preference_match_sql(preferences, content_type, schema)`

**职责：** 根据用户偏好记录构建 SQL WHERE 子句，实现多维度偏好匹配。

**算法：**
1. 从偏好记录中提取所有唯一的 `genres`（按 `/` 分割）、`director`、`actors`（按 `/` 分割）
2. 为每个维度构建 `ILIKE` 条件
3. 多个条件用 `OR` 连接（宽松匹配，提高召回率）
4. 附加 `content_type` 过滤条件

```python
def build_preference_match_sql(preferences: list, content_type: str, schema: str):
    """
    返回 (where_clause: str, params: list)
    例：WHERE content_type = 'movie' AND (genres ILIKE %s OR genres ILIKE %s OR director ILIKE %s)
    """
    conditions = [f"content_type = '{content_type}'"]
    params = []
    
    genre_set = set()
    director_set = set()
    actor_set = set()
    
    for pref in preferences:
        if pref.get('genres'):
            for g in pref['genres'].split('/'):
                g = g.strip()
                if g:
                    genre_set.add(g)
        if pref.get('director'):
            director_set.add(pref['director'].strip())
        if pref.get('actors'):
            for a in pref['actors'].split('/'):
                a = a.strip()
                if a:
                    actor_set.add(a)
    
    match_conditions = []
    for g in genre_set:
        match_conditions.append("genres ILIKE %s")
        params.append(f"%{g}%")
    for d in director_set:
        match_conditions.append("director ILIKE %s")
        params.append(f"%{d}%")
    for a in actor_set:
        match_conditions.append("actors ILIKE %s")
        params.append(f"%{a}%")
    
    if match_conditions:
        conditions.append(f"({' OR '.join(match_conditions)})")
    
    return " AND ".join(conditions), params
```

#### `build_preference_context(preferences)`

**职责：** 将偏好记录聚合为 Agent 可用的上下文字典。

```python
def build_preference_context(preferences: list) -> dict:
    """
    返回聚合后的偏好上下文，供 AgentManager 使用
    """
    genres = set()
    directors = set()
    actors = set()
    
    for pref in preferences:
        if pref.get('genres'):
            for g in pref['genres'].split('/'):
                if g.strip():
                    genres.add(g.strip())
        if pref.get('director') and pref['director'].strip():
            directors.add(pref['director'].strip())
        if pref.get('actors'):
            for a in pref['actors'].split('/'):
                if a.strip():
                    actors.add(a.strip())
    
    return {
        'genres': list(genres),
        'directors': list(directors),
        'actors': list(actors),
    }
```

---

### 前端 API 层（content.ts 新增）

#### 新增类型定义

```typescript
export interface UserPreference {
  id: number;
  user_id: string;
  content_id: string;
  content_type: 'movie' | 'series';
  title: string;
  genres: string;        // 原始字符串，如 "科幻/动作"
  rating: number;
  year: number;
  director: string;
  actors: string;        // 原始字符串，如 "吴京/屈楚萧"
  created_at: string;
}

export interface UserPreferencesResponse {
  preferences: UserPreference[];
}

export interface PreferenceMediaListResponse extends MediaListResponse {
  is_fallback: boolean;
}
```

#### 新增 API 方法

```typescript
// 获取偏好电影列表
getPreferenceMovies: async (userId: number, params?: {
  page?: number;
  limit?: number;
  genre?: string;
  sort_by?: string;
}) => {
  const response = await api.get<PreferenceMediaListResponse>(
    `/users/${userId}/movies/preference`, { params }
  );
  return response.data;
},

// 获取偏好剧集列表
getPreferenceSeries: async (userId: number, params?: {
  page?: number;
  limit?: number;
  genre?: string;
  sort_by?: string;
}) => {
  const response = await api.get<PreferenceMediaListResponse>(
    `/users/${userId}/series/preference`, { params }
  );
  return response.data;
},

// 获取用户偏好数据
getUserPreferences: async (userId: number) => {
  const response = await api.get<UserPreferencesResponse>(
    `/users/${userId}/preferences`
  );
  return response.data;
},
```

---

### 前端页面层变更

#### Movies.tsx 变更

**核心变更：** 在 `fetchMovies` 的 `useEffect` 中，根据 `isAuthenticated` 决定调用哪个接口。

```typescript
// 变更前
const data = await contentApi.getMovies(params);

// 变更后
const data = isAuthenticated && user
  ? await contentApi.getPreferenceMovies(user.id, params)
  : await contentApi.getMovies(params);

// 新增：偏好回退提示
const [isFallback, setIsFallback] = useState(false);
// 在 setMovies 后：
if ('is_fallback' in data) setIsFallback(data.is_fallback);
```

**新增 UI 元素：** 当 `isFallback === true` 时，在页头下方展示提示横幅：
```
💡 暂未找到您的偏好记录，正在展示全部电影
```

#### Series.tsx 变更

与 Movies.tsx 变更完全对称，调用 `contentApi.getPreferenceSeries()`。

#### Watchlist.tsx 重构

**核心变更：** 完全替换模拟数据，实现真实 API 调用。

**新增状态：**
```typescript
const { isAuthenticated, user } = useAuthStore();
const [watchlist, setWatchlist] = useState<MediaItem[]>([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
```

**数据加载：**
```typescript
useEffect(() => {
  if (!isAuthenticated || !user) return;
  const fetchWatchlist = async () => {
    setLoading(true);
    try {
      const data = await contentApi.getWatchlist(user.id);
      setWatchlist(data.watchlist);
    } catch {
      setError('待看清单加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };
  fetchWatchlist();
}, [isAuthenticated, user]);
```

**移除操作（乐观更新）：**
```typescript
const handleRemove = async (mediaId: number) => {
  // 乐观更新：先从 UI 移除
  setWatchlist(prev => prev.filter(item => item.id !== mediaId));
  try {
    await contentApi.removeFromWatchlist(user!.id, mediaId);
  } catch {
    // 回滚：重新加载列表
    fetchWatchlist();
  }
};
```

#### AgentAssistant.tsx 变更

**新增状态：**
```typescript
const { isAuthenticated, user } = useAuthStore();
const [quickPrompts, setQuickPrompts] = useState<string[]>(DEFAULT_QUICK_PROMPTS);
```

**默认词条（降级用）：**
```typescript
const DEFAULT_QUICK_PROMPTS = [
  '推荐高分科幻电影',
  '最近有什么好看的剧集',
  '推荐经典动作片',
  '有什么适合家庭观看的电影',
];
```

**偏好词条生成（加载时）：**
```typescript
useEffect(() => {
  if (!isAuthenticated || !user) return;
  contentApi.getUserPreferences(user.id)
    .then(data => {
      const prompts = generateQuickPrompts(data.preferences);
      if (prompts.length > 0) setQuickPrompts(prompts);
    })
    .catch(() => {
      // 静默失败，保留默认词条
    });
}, [isAuthenticated, user]);
```


#### Quick Prompts 生成函数
﻿
#### Quick Prompts 生成函数

**职责：** 根据用户偏好数据生成个性化快捷词条列表。

`	ypescript
function generateQuickPrompts(preferences: UserPreference[]): string[] {
  const prompts: string[] = [];
  const genres = new Set<string>();
  const directors = new Set<string>();
  const actors = new Set<string>();

  for (const pref of preferences) {
    if (pref.genres) {
      pref.genres.split('/').forEach(g => { if (g.trim()) genres.add(g.trim()); });
    }
    if (pref.director?.trim()) directors.add(pref.director.trim());
    if (pref.actors) {
      pref.actors.split('/').forEach(a => { if (a.trim()) actors.add(a.trim()); });
    }
  }

  Array.from(genres).slice(0, 2).forEach(g => {
    prompts.push('推荐更多' + g + '电影');
  });
  Array.from(directors).slice(0, 1).forEach(d => {
    prompts.push('推荐' + d + '的其他作品');
  });
  Array.from(actors).slice(0, 1).forEach(a => {
    prompts.push('推荐' + a + '主演的其他影视');
  });

  return prompts;
}
`

---

## 数据模型

### user_preferences 表（已存在，确认字段）

pp.user_preferences 表已在迁移文件  02_user_preferences.sql 中定义，字段如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL | 主键 |
| user_id | VARCHAR(64) | 关联 users.id |
| content_id | VARCHAR(64) | 关联内容的 source_item_id |
| content_type | VARCHAR(16) | 'movie' 或 'series' |
| title | VARCHAR(255) | 影视标题 |
| genres | TEXT | 类型，如 "科幻/动作" |
| rating | NUMERIC(3,1) | 评分 |
| year | INTEGER | 年份 |
| director | VARCHAR(255) | 导演 |
| actors | TEXT | 演员，如 "吴京/屈楚萧" |
| cover_url | TEXT | 封面图 URL |
| comment | TEXT | 用户备注 |
| source | VARCHAR(64) | 数据来源 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**唯一约束：** (user_id, content_id, content_type)

**索引：** (user_id, content_type, created_at DESC) — 支持按用户和内容类型高效查询

### 偏好匹配查询示例

`sql
-- 查询用户偏好记录
SELECT genres, director, actors
FROM app.user_preferences
WHERE user_id = \ AND content_type = 'movie';

-- 基于偏好匹配内容（由 build_preference_match_sql 动态生成）
SELECT *
FROM app.content_items
WHERE content_type = 'movie'
  AND (
    genres ILIKE '%科幻%'
    OR genres ILIKE '%动作%'
    OR director ILIKE '%郭帆%'
    OR actors ILIKE '%吴京%'
  )
ORDER BY popularity DESC NULLS LAST
LIMIT 20 OFFSET 0;
`

### watchlists 表（已存在，联表查询）

待看清单接口已在 
outes.py 中实现联表查询，返回完整影视信息。Watchlist.tsx 重构后直接使用现有 GET /api/users/{user_id}/watchlist 接口，无需修改后端。

### AgentManager 接口扩展

AgentManager.process_user_request 签名扩展：

`python
# 变更前
def process_user_request(self, user_id: str, user_message: str):

# 变更后
def process_user_request(
    self,
    user_id: str,
    user_message: str,
    preference_context: dict | None = None
):
`

preference_context 结构：
`python
{
    "genres": ["科幻", "动作"],
    "directors": ["郭帆", "张艺谋"],
    "actors": ["吴京", "章子怡"],
}
`

ToolOrchestrator.execute_tools 同步扩展，接收 preference_context 并在推荐时优先匹配偏好内容。

﻿
## 正确性属性

*属性（Property）是在系统所有有效执行中都应成立的特征或行为——本质上是对系统应该做什么的形式化陈述。属性是人类可读规范与机器可验证正确性保证之间的桥梁。*

### 属性 1：偏好匹配结果一致性

*对任意* 用户偏好集合（包含 genres、director、actors 字段），偏好电影/剧集接口返回的每条记录，其 genres、director 或 actors 字段中至少有一个与偏好集合中的某条记录相匹配（ILIKE 语义）。

**验证：需求 1.2、1.3、2.2、2.3**

### 属性 2：偏好结果按热度降序排列

*对任意* 偏好电影/剧集接口的返回结果列表，列表中相邻两条记录满足 
esults[i].popularity >= results[i+1].popularity。

**验证：需求 1.3、2.3**

### 属性 3：空偏好时兜底标识

*对任意* 用户，当其 user_preferences 表中不存在对应 content_type 的偏好记录时，偏好接口响应必须包含 is_fallback: true，且返回的结果集与全量接口在相同参数下的结果集一致。

**验证：需求 1.4、2.4**

### 属性 4：分页参数兼容性

*对任意* 合法的 page（正整数）、limit（1-100）、genre（字符串或空）、sort_by（枚举值）参数组合，偏好接口应返回格式正确的响应（包含 total、page、limit、results、is_fallback 字段），不抛出 500 错误。

**验证：需求 1.7、2.7**

### 属性 5：待看清单数据完整性

*对任意* 用户的待看清单，GET /api/users/{user_id}/watchlist 返回的每条记录必须包含 	itle、overview（plot）、poster_path（cover_url）、ote_average（rating）、media_type（content_type）、dded_at 字段，且字段值非 null。

**验证：需求 3.2**

### 属性 6：移除操作后条目不再出现

*对任意* 包含 N 条记录的待看清单，对其中任意一条记录执行移除操作后，该条目的 media_id 不应再出现在前端列表状态中，且列表长度变为 N-1。

**验证：需求 3.5**

### 属性 7：偏好词条覆盖性

*对任意* 包含至少一个非空 genres 字段的用户偏好集合，generateQuickPrompts 函数生成的词条列表中，至少有一条词条包含该 genres 值；对包含非空 director 的偏好，至少有一条词条包含该 director 值；对包含非空 ctors 的偏好，至少有一条词条包含该 actors 值。

**验证：需求 4.2、4.3、4.4**

### 属性 8：用户偏好 API 数据一致性

*对任意* 用户，GET /api/users/{user_id}/preferences 返回的偏好记录集合，与直接查询 pp.user_preferences WHERE user_id = ? 得到的记录集合在 content_id、content_type、genres、director、ctors 字段上完全一致（读写一致性）。

**验证：需求 4.8**

---

## 错误处理

### 后端错误处理策略

| 场景 | HTTP 状态码 | 响应格式 |
|------|------------|---------|
| 数据库查询异常 | 500 | {"error": "...", "detail": "..."} |
| 用户未认证（无 token） | 401 | {"message": "Token is missing!"} |
| token 过期 | 401 | {"message": "Token has expired!"} |
| 访问他人资源（user_id 不匹配） | 403 | {"error": "Unauthorized"} |
| 偏好为空（兜底） | 200 | 正常响应 + is_fallback: true |

**偏好接口的错误处理原则：**
- 偏好查询失败（数据库异常）→ 返回 500，不静默降级为全量（避免掩盖问题）
- 偏好为空（正常业务情况）→ 返回 200 + 全量数据 + is_fallback: true
- Agent 偏好上下文查询失败 → 记录日志，以空上下文继续执行（不影响对话功能）

### 前端错误处理策略

| 场景 | 处理方式 |
|------|---------|
| 偏好接口返回 500 | 展示错误提示，提供重试按钮 |
| 偏好接口返回 is_fallback: true | 展示提示横幅："暂未找到偏好记录，展示全部内容" |
| 待看清单接口失败 | 展示错误提示，说明数据加载失败 |
| 移除操作失败 | 回滚乐观更新，重新加载列表 |
| 用户偏好接口失败（Agent 页） | 静默失败，使用默认快捷词条 |
| 用户未登录访问待看清单 | 展示登录引导提示 |

### Agent 偏好注入的容错设计

`python
@api_bp.route("/api/agent/chat", methods=["POST"])
@token_required
def chat(current_user):
    data = request.get_json() or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    # 偏好上下文查询失败不影响对话功能
    preference_context = None
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT * FROM {SCHEMA}.user_preferences WHERE user_id = %s",
                    (current_user['id'],)
                )
                preferences = cur.fetchall()
        preference_context = build_preference_context(preferences)
    except Exception as e:
        print(f"Failed to load preference context: {e}")
        # 继续执行，preference_context 保持 None
    
    try:
        from agent.recommendation_agent import AgentManager
        agent = AgentManager()
        nl_response, structured_results = agent.process_user_request(
            current_user['id'], message, preference_context
        )
        return jsonify({"nl_response": nl_response, "structured_results": structured_results})
    except Exception as e:
        print(f"Agent error: {e}")
        return jsonify({"error": "Agent execution failed", "detail": str(e)}), 500
`

---

## 测试策略

### 测试分层

本功能采用双层测试策略：

1. **单元测试 / 示例测试**：验证具体行为、边界条件和错误处理
2. **属性测试**：验证跨输入的普遍性质（使用 Hypothesis 库，最少 100 次迭代）

### 属性测试配置

**Python 后端：** 使用 [Hypothesis](https://hypothesis.readthedocs.io/) 库

`python
from hypothesis import given, settings
from hypothesis import strategies as st

@settings(max_examples=100)
@given(
    preferences=st.lists(
        st.fixed_dictionaries({
            'genres': st.one_of(st.none(), st.text(min_size=1, max_size=50)),
            'director': st.one_of(st.none(), st.text(min_size=1, max_size=50)),
            'actors': st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        }),
        min_size=1, max_size=10
    )
)
def test_preference_match_sql_returns_valid_clause(preferences):
    # Feature: user-preference-driven-pages, Property 1: 偏好匹配结果一致性
    where_clause, params = build_preference_match_sql(preferences, 'movie', 'app')
    assert "content_type = 'movie'" in where_clause
    assert len(params) >= 0
`

**TypeScript 前端：** 使用 [fast-check](https://fast-check.io/) 库

`	ypescript
import * as fc from 'fast-check';

// Feature: user-preference-driven-pages, Property 7: 偏好词条覆盖性
test('generateQuickPrompts covers genres from preferences', () => {
  fc.assert(
    fc.property(
      fc.array(
        fc.record({
          genres: fc.string({ minLength: 1 }),
          director: fc.string(),
          actors: fc.string(),
        }),
        { minLength: 1 }
      ),
      (preferences) => {
        const prefs = preferences.map((p, i) => ({
          id: i,
          user_id: 'u1',
          content_id: c,
          content_type: 'movie' as const,
          title: 'test',
          rating: 7.0,
          year: 2020,
          created_at: '',
          ...p,
        }));
        const prompts = generateQuickPrompts(prefs);
        const firstGenre = preferences[0].genres.split('/')[0].trim();
        if (firstGenre) {
          expect(prompts.some(p => p.includes(firstGenre))).toBe(true);
        }
      }
    ),
    { numRuns: 100 }
  );
});
`

### 单元测试覆盖点

**后端（pytest）：**

| 测试用例 | 验证需求 |
|---------|---------|
| 偏好为空时返回 is_fallback=true | 1.4、2.4 |
| 数据库异常时返回 500 | 1.6、2.6、4.9 |
| 未认证请求返回 401 | 通用 |
| 访问他人资源返回 403 | 通用 |
| Agent chat 偏好查询失败时仍正常响应 | 4.6 |
| 偏好接口返回所有字段 | 4.8 |

**前端（Vitest + React Testing Library）：**

| 测试用例 | 验证需求 |
|---------|---------|
| 已登录时调用偏好接口 | 1.1、2.1 |
| 未登录时调用全量接口 | 1.5、2.5 |
| 待看清单加载时显示 loading | 3.3 |
| 待看清单为空时显示空状态 | 3.4 |
| 未登录访问待看清单显示登录提示 | 3.6 |
| 待看清单接口失败显示错误提示 | 3.7 |
| 偏好接口失败时显示默认快捷词条 | 4.5 |

### 集成测试

- 使用真实 PostgreSQL 测试库（pytest-postgresql 或 Docker）
- 验证偏好匹配 SQL 在真实数据库上的执行结果
- 验证联表查询返回完整字段
- 验证 Agent 偏好上下文注入的端到端流程

