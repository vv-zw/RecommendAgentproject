# 需求文档：多 Agent 协作推荐架构

## 简介

本文档描述将现有影视推荐系统的单一 AgentManager 升级为多 Agent 协作架构的功能需求。

现有系统采用线性链路：`NLUProcessor → ToolOrchestrator → ResponseGenerator`，由单一 `AgentManager` 统一协调。该架构存在两个核心痛点：

1. **NLU 被动解析**：`NLUProcessor` 仅将用户输入解析为 JSON 结构，无法在需求模糊时主动追问，导致推荐结果与用户真实意图偏差较大。
2. **推荐策略单一**：无论用户是明确查询（"最近有什么高分电影"）还是模糊需求（"今晚看什么好"），系统都强制注入用户偏好，导致明确查询场景下推荐效果差。

改造目标是引入职责单一的多 Agent 协作架构，通过 Router Agent 分发意图、需求分析 Agent 主动追问、推荐 Agent 动态调整策略，从根本上解决上述问题。

## 词汇表

- **Router_Agent**：路由 Agent，负责接收用户输入并将其分发到对应的下游 Agent
- **Analysis_Agent**：需求分析 Agent，负责主动理解用户需求并在必要时追问
- **Recommendation_Agent**：推荐 Agent，负责基于结构化需求执行工具调用并返回推荐结果
- **Explanation_Agent**：解释 Agent，负责为每条推荐结果生成个性化推荐理由
- **Chitchat_Agent**：闲聊 Agent，负责处理与影视推荐无关的日常对话
- **AgentOrchestrator**：多 Agent 编排器，替换现有 `AgentManager`，协调各 Agent 的调用顺序
- **StructuredContext**：结构化需求上下文，由 Analysis_Agent 输出，包含 `intent`、`mood`、`genres`、`context`、`confidence` 等字段
- **RecommendationStrategy**：推荐策略，根据用户意图类型动态选择的检索和排序方式
- **Session**：多轮对话会话，由现有 `SessionManager` 管理
- **confidence**：需求置信度，Analysis_Agent 对当前需求清晰程度的评估，取值为 `high`、`medium`、`low`
- **intent_type**：意图类型，Router_Agent 判断的用户意图分类，包括 `explicit_query`（明确查询）、`vague_recommendation`（模糊推荐）、`mixed`（混合）、`chitchat`（闲聊）

---

## 需求

### 需求 1：Router Agent 意图路由

**用户故事：** 作为用户，我希望系统能准确识别我的意图类型，以便将我的请求路由到最合适的处理流程，从而获得更精准的响应。

#### 验收标准

1. WHEN 用户发送消息，THE Router_Agent SHALL 将意图分类为以下四种类型之一：`explicit_query`（明确查询）、`vague_recommendation`（模糊推荐）、`mixed`（混合）、`chitchat`（闲聊）
2. WHEN Router_Agent 判断意图为 `explicit_query`，THE Router_Agent SHALL 将请求直接路由到 Recommendation_Agent，并附带 `skip_preference_injection=true` 标记
3. WHEN Router_Agent 判断意图为 `vague_recommendation`，THE Router_Agent SHALL 将请求路由到 Analysis_Agent 进行需求分析
4. WHEN Router_Agent 判断意图为 `mixed`，THE Router_Agent SHALL 将请求路由到 Analysis_Agent，由 Analysis_Agent 决定是否需要追问
5. WHEN Router_Agent 判断意图为 `chitchat`，THE Router_Agent SHALL 将请求路由到 Chitchat_Agent
6. THE Router_Agent SHALL 在单次 LLM 调用中完成意图分类，调用温度参数不超过 0.2 以确保分类稳定性
7. IF Router_Agent 的 LLM 调用失败，THEN THE Router_Agent SHALL 将意图降级为 `vague_recommendation` 并继续处理流程

---

### 需求 2：需求分析 Agent 主动追问

**用户故事：** 作为用户，我希望当我的需求不够清晰时，系统能主动询问我的偏好，而不是直接给出不相关的推荐，以便获得真正符合我心意的内容。

#### 验收标准

1. WHEN Analysis_Agent 接收到用户需求，THE Analysis_Agent SHALL 评估需求清晰度并输出 `confidence` 字段，取值为 `high`、`medium`、`low`
2. WHEN Analysis_Agent 评估 `confidence` 为 `low`，THE Analysis_Agent SHALL 向用户提出至多 2 个追问问题，追问内容涵盖类型、心情、偏好导演或演员等维度
3. WHEN Analysis_Agent 评估 `confidence` 为 `high`，THE Analysis_Agent SHALL 直接输出 StructuredContext 而不再追问
4. WHEN 用户回答追问后，THE Analysis_Agent SHALL 结合历史对话更新 StructuredContext 并重新评估 `confidence`
5. THE Analysis_Agent SHALL 在累计追问不超过 3 轮后输出最终 StructuredContext，无论 `confidence` 是否达到 `high`
6. THE Analysis_Agent SHALL 输出包含以下字段的 StructuredContext：`intent`、`mood`、`genres`、`context`、`confidence`、`content_type`、`keywords`、`directors`、`actors`
7. IF Analysis_Agent 的 LLM 调用失败，THEN THE Analysis_Agent SHALL 使用用户原始输入构造最小化 StructuredContext 并将 `confidence` 设为 `low`

---

### 需求 3：推荐策略动态调整

**用户故事：** 作为用户，我希望当我明确查询"最近高分电影"时，系统直接按评分检索全库，而不是强制混入我的历史偏好，以便获得客观准确的查询结果。

#### 验收标准

1. WHEN Recommendation_Agent 接收到 `skip_preference_injection=true` 标记，THE Recommendation_Agent SHALL 按查询条件（评分、类型、片名等）直接检索全库，不将用户偏好作为强制过滤条件
2. WHEN Recommendation_Agent 执行明确查询策略，THE Recommendation_Agent SHALL 仅在同等条件下将用户偏好作为次级排序因子，权重不超过总排序权重的 20%
3. WHEN Recommendation_Agent 接收到 `skip_preference_injection=false` 且 `confidence` 为 `high` 的 StructuredContext，THE Recommendation_Agent SHALL 优先使用用户偏好进行个性化检索
4. WHEN Recommendation_Agent 接收到 `confidence` 为 `medium` 或 `low` 的 StructuredContext，THE Recommendation_Agent SHALL 同时执行偏好检索和通用检索，并对结果进行合并去重
5. THE Recommendation_Agent SHALL 基于 StructuredContext 中的 `mood` 和 `context` 字段选择合适的检索工具（`semantic_search` 优先用于情绪/氛围描述，`search_content` 优先用于关键词查询）
6. THE Recommendation_Agent SHALL 在单次请求中最多执行 5 次工具调用循环（与现有 `MAX_TOOL_ITERATIONS` 保持一致）
7. IF 所有工具调用均返回空结果，THEN THE Recommendation_Agent SHALL 执行一次无过滤条件的全库热门内容兜底查询

---

### 需求 4：解释 Agent 上下文感知推荐理由

**用户故事：** 作为用户，我希望每条推荐结果都有一句贴合我当前心情和需求的推荐理由，而不是千篇一律的模板文字，以便更好地决定是否观看。

#### 验收标准

1. WHEN Explanation_Agent 接收到推荐结果列表，THE Explanation_Agent SHALL 为每条结果生成长度在 20 至 50 字之间的个性化推荐理由
2. WHEN StructuredContext 包含非空的 `mood` 字段，THE Explanation_Agent SHALL 在推荐理由中体现该情绪维度（如"适合今晚放松心情"）
3. WHEN StructuredContext 包含非空的 `context` 字段，THE Explanation_Agent SHALL 在推荐理由中结合该场景信息（如"适合和家人一起观看"）
4. THE Explanation_Agent SHALL 在单次 LLM 调用中批量处理最多 8 条推荐结果的理由生成
5. IF Explanation_Agent 的 LLM 调用失败，THEN THE Explanation_Agent SHALL 使用现有模板降级逻辑（`_template_explanation`）为每条结果生成兜底理由
6. THE Explanation_Agent SHALL 在推荐理由中优先突出与用户需求最相关的影视特征（类型、导演、评分、剧情主题等）

---

### 需求 5：闲聊 Agent 独立处理

**用户故事：** 作为用户，我希望在与推荐助手闲聊时，系统能自然地回应，并在适当时机引导我提出推荐需求，而不是强行执行推荐流程。

#### 验收标准

1. WHEN Chitchat_Agent 接收到闲聊消息，THE Chitchat_Agent SHALL 用自然流畅的中文回复，回复长度不超过 150 字
2. WHEN 用户的闲聊内容涉及影视相关话题，THE Chitchat_Agent SHALL 在回复中自然地引导用户提出具体推荐需求
3. THE Chitchat_Agent SHALL 不调用任何推荐工具（`search_content`、`semantic_search` 等）
4. IF Chitchat_Agent 的 LLM 调用失败，THEN THE Chitchat_Agent SHALL 返回固定的友好提示语，引导用户提出推荐需求

---

### 需求 6：AgentOrchestrator 统一编排

**用户故事：** 作为开发者，我希望有一个统一的编排入口协调各 Agent 的调用顺序和数据传递，以便在不修改 API 层的前提下完成架构升级。

#### 验收标准

1. THE AgentOrchestrator SHALL 提供与现有 `AgentManager.process_user_request` 完全相同的方法签名，包括参数 `user_id`、`user_message`、`preference_context`、`session_id`、`stream`，以及返回值 `(nl_response, structured_results, session_id)`
2. THE AgentOrchestrator SHALL 按照 Router_Agent → Analysis_Agent（条件触发）→ Recommendation_Agent → Explanation_Agent 的顺序协调各 Agent
3. WHEN `stream=True`，THE AgentOrchestrator SHALL 将 Recommendation_Agent 的流式输出透传给调用方，与现有 SSE 机制保持兼容
4. THE AgentOrchestrator SHALL 复用现有 `SessionManager` 管理多轮对话历史，不引入新的 Session 存储机制
5. THE AgentOrchestrator SHALL 将 Analysis_Agent 的追问消息通过与普通 assistant 消息相同的通道返回给前端，`structured_results` 字段在追问轮次中返回空列表
6. IF 任意 Agent 抛出未捕获异常，THEN THE AgentOrchestrator SHALL 记录错误日志并返回友好的错误提示，不向前端暴露内部异常信息

---

### 需求 7：向后兼容与 API 不变性

**用户故事：** 作为前端开发者，我希望 Agent 架构升级后 `/api/agent/chat` 接口的请求和响应格式保持不变，以便无需修改前端代码。

#### 验收标准

1. THE AgentOrchestrator SHALL 保持 `/api/agent/chat` 接口的请求字段不变：`message`、`session_id`、`stream`
2. THE AgentOrchestrator SHALL 保持非流式响应的字段不变：`nl_response`、`structured_results`、`session_id`
3. THE AgentOrchestrator SHALL 保持 SSE 流式响应的事件格式不变：`meta` 事件包含 `session_id` 和 `structured_results`，`token` 事件包含 `content`，结束标记为 `[DONE]`
4. THE AgentOrchestrator SHALL 保持 `structured_results` 中每条记录的字段结构不变：`id`、`title`、`overview`、`poster_path`、`vote_average`、`media_type`、`genres`、`explanation` 等
5. WHEN 多 Agent 架构部署后，THE AgentOrchestrator SHALL 通过现有 `api/routes.py` 中的 `chat` 路由函数调用，无需修改路由层代码
