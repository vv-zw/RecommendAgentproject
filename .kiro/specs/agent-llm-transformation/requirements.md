# 需求文档

## 简介

本项目是一个基于 Flask + React + PostgreSQL 的影视推荐系统。后端已有完整的 API 层（api/）、豆瓣爬虫（crawler/，已爬取约 1233 条影视数据）和前端界面（frontend/）。

当前 Agent 模块（agent/）存在以下核心问题：

- **NLUProcessor** 仅识别英文关键词，无法处理中文用户输入
- **ToolOrchestrator** 直接执行 SQL 查询，未接入任何 AI 模型
- **ResponseGenerator** 仅拼接模板字符串，不是真正的 AI 生成
- 未接入任何 LLM，无 API Key 配置
- 无多轮对话记忆，每次对话独立
- explain/、strategy_selector.py、intent_parser.py 等模块已写好但未接入主流程
- RAG 模块基于本地 JSON 文件和自制 TF-IDF，未使用向量数据库

**改造目标**：将 Agent 模块升级为真正的 LLM 驱动的智能推荐助手，支持中文自然语言理解、Function Calling 工具调用、多轮对话记忆、语义向量检索（RAG）和推荐可解释性，并清理历史遗留冗余代码。

## 词汇表

- **Agent**：本系统中的智能对话推荐助手，负责理解用户意图并返回推荐结果
- **LLM**（Large Language Model）：大语言模型，本项目使用 DeepSeek API
- **NLU**（Natural Language Understanding）：自然语言理解，将用户输入解析为结构化意图和实体
- **Intent**：用户意图，如推荐电影、搜索内容、添加待看清单等
- **Entity**：从用户输入中提取的关键信息，如类型、导演、演员、情绪描述等
- **Function Calling**：LLM 的工具调用能力，允许模型自主决定调用哪个工具及传入什么参数
- **ReAct**：Reasoning + Acting 模式，LLM 先推理再执行工具调用的 Agent 架构
- **RAG**（Retrieval-Augmented Generation）：检索增强生成，结合向量检索为 LLM 提供上下文
- **pgvector**：PostgreSQL 的向量扩展，支持存储和检索高维向量
- **Embedding**：将文本转换为高维向量的过程，用于语义相似度计算
- **Session**：一次完整的对话会话，包含多轮用户与 Agent 的交互历史
- **滑动窗口**：控制传入 LLM 的历史消息数量，避免超出 token 限制
- **SSE**（Server-Sent Events）：服务器推送事件，用于实现流式输出
- **NLUProcessor**：agent/agent_core/nlu_processor.py 中的意图理解组件
- **ToolOrchestrator**：agent/agent_core/tool_orchestrator.py 中的工具编排组件
- **ResponseGenerator**：agent/agent_core/response_generator.py 中的回复生成组件
- **AgentManager**：agent/recommendation_agent.py 中的 Agent 主入口类
- **RagEngine**：rag/rag_engine.py 中的 RAG 检索引擎
- **ExplanationGenerator**：explain/explanation_generator.py 中的推荐解释生成组件
- **content_items**：PostgreSQL 中存储影视内容的主表
- **DeepSeek**：本项目选用的 LLM 提供商，支持 Function Calling，国内访问速度快

## 需求

---

### 需求 0：代码清理与项目结构整理

**用户故事：** 作为开发者，我希望清理历史遗留的冗余代码和文件，以便项目结构清晰、便于后续 LLM 改造工作的开展。

#### 待删除文件清单

**完全冗余，可直接删除：**

| 文件/目录 | 原因 |
|---|---|
| mock_recommenders/ 目录（ncf.py, textcnn.py, rule_based.py, __init__.py） | 接入 LLM 后不再需要 mock 推荐器 |
| orchestrator/ 目录（recommendation_orchestrator.py, fusion.py, filter.py, score_engine.py） | 旧的融合逻辑，被 LLM Function Calling 替代 |
| agent/intent_parser.py | 与 agent_core/nlu_processor.py 功能重复，且均未接入主流程 |
| agent/strategy_selector.py | 策略选择逻辑将由 LLM 自主决定，不再需要手工规则 |
| ai_config/settings.py 中的 FUSION_WEIGHTS 相关配置 | 融合权重在 LLM 架构下不再适用 |
| movie_recommendation/NeuralCollaborativeFiltering.py | 旧的 NCF 模型，已废弃 |
| movie_recommendation/TextCNN.py | 旧的 TextCNN 模型，已废弃 |
| movie_recommendation/app.py | 旧的 Flask 应用，已被 api/app.py 替代 |
| movie_recommendation/recommendation/ 目录 | 旧的推荐引擎，已废弃 |
| 微信小程序/ 目录 | 已废弃的小程序代码 |
| data/recommendations/movie_recommendations.json | 旧的静态推荐结果文件 |
| data/recommendations/series_recommendations.json | 旧的静态推荐结果文件 |
| movie_recommendation/data/movie_recommendations.json | 旧的数据文件 |
| movie_recommendation/data/series_recommendations.json | 旧的数据文件 |
| movie_recommendation/data/user_data.json | 旧的数据文件 |
| write_design_part3.py、design_part3.txt | 临时设计文件 |
| check_users.py、check_crawl_result.py | 调试脚本，爬虫完成后可删除 |
| 安装TensorFlow.bat、启动应用-Python312.bat | 旧的启动脚本 |

**RAG 模块需重构（保留目录，重写实现）：**

| 文件 | 现状 | 处理方式 |
|---|---|---|
| rag/embedding.py | 自制 TF-IDF 向量化 | 改为调用 DeepSeek/OpenAI Embedding API |
| rag/retriever.py | 基于本地 movies.json 文件检索 | 改为查询 PostgreSQL + pgvector |
| rag/rag_engine.py | 入口，依赖旧 retriever | 重写，接入新的向量检索逻辑 |
| rag/similarity.py | 余弦相似度计算 | 保留，可复用 |

#### 验收标准

1. WHEN 代码清理完成后，THE 项目 SHALL 不包含上述待删除文件和目录
2. WHEN 代码清理完成后，THE 项目 SHALL 能够正常启动（api/app.py 无导入错误）
3. IF 删除 mock_recommenders/ 目录，THEN THE 系统 SHALL 不存在任何对该目录的导入引用
4. IF 删除 orchestrator/ 目录，THEN THE 系统 SHALL 不存在任何对该目录的导入引用
5. WHEN ai_config/settings.py 清理完成后，THE 文件 SHALL 仅保留 DATABASE_URL、DEBUG_MODE_ENABLED、EXPLAIN_ENABLED、LOG_FILE_PATH、LOG_LEVEL 等有效配置项

---

### 需求 1：LLM 接入与配置

**用户故事：** 作为开发者，我希望将 DeepSeek LLM 接入系统，以便后续所有 AI 功能模块都能调用真实的大语言模型能力。

#### 验收标准

1. THE 系统 SHALL 在 `.env` 文件中支持 `DEEPSEEK_API_KEY` 和 `LLM_PROVIDER` 配置项
2. THE 系统 SHALL 在 `ai_config/settings.py` 中提供统一的 LLM 客户端初始化入口，读取上述环境变量
3. WHEN `DEEPSEEK_API_KEY` 未配置，THE 系统 SHALL 在启动时输出明确的警告日志，提示用户配置 API Key
4. WHEN `LLM_PROVIDER` 设置为 `deepseek`，THE LLM 客户端 SHALL 使用 DeepSeek API 端点和 `deepseek-chat` 模型
5. WHERE `LLM_PROVIDER` 支持扩展，THE 系统 SHALL 支持通过配置切换至 `openai` 等其他兼容 OpenAI 接口的提供商
6. THE LLM 客户端 SHALL 支持设置 `temperature`、`max_tokens` 等基础参数
7. IF LLM API 调用失败（网络错误、超时、鉴权失败），THEN THE 系统 SHALL 捕获异常并返回结构化错误信息，不抛出未处理异常

### 需求 2：NLUProcessor 中文意图理解改造

**用户故事：** 作为用户，我希望用中文向 Agent 描述我的需求，以便 Agent 能准确理解我的意图并给出合适的推荐。

#### 验收标准

1. WHEN 用户发送中文消息，THE NLUProcessor SHALL 调用 LLM 将其解析为结构化 JSON，包含 `intent` 和 `entities` 字段
2. THE NLUProcessor SHALL 支持识别以下意图类型：`recommend_movie`、`recommend_series`、`search_content`、`add_to_watchlist`、`get_detail`、`chitchat`
3. THE NLUProcessor SHALL 从用户输入中提取以下实体：`genres`（类型列表）、`directors`（导演列表）、`actors`（演员列表）、`keywords`（关键词列表）、`mood`（情绪描述）、`content_title`（具体影视名称）
4. WHEN 用户输入为"推荐几部科幻电影"，THE NLUProcessor SHALL 返回 `intent: recommend_movie`，`entities.genres: ["科幻"]`
5. WHEN 用户输入为"有没有类似流浪地球的电影"，THE NLUProcessor SHALL 返回 `intent: recommend_movie`，`entities.keywords: ["流浪地球"]`
6. IF LLM 返回的 JSON 格式不合法，THEN THE NLUProcessor SHALL 进行容错处理，返回 `intent: unknown` 而非抛出异常
7. THE NLUProcessor SHALL 不再使用英文关键词匹配逻辑（删除原有 `if "recommend" in text` 等规则）

### 需求 3：ResponseGenerator LLM 自然语言回复改造

**用户故事：** 作为用户，我希望 Agent 的回复是自然流畅的中文，而不是固定的模板句子，以便获得更好的对话体验。

#### 验收标准

1. WHEN ResponseGenerator 生成回复，THE ResponseGenerator SHALL 调用 LLM 生成自然语言文本，而非拼接模板字符串
2. THE ResponseGenerator SHALL 将用户意图、工具调用结果和用户偏好上下文作为 prompt 传入 LLM
3. WHEN 工具返回推荐结果列表，THE ResponseGenerator SHALL 生成包含推荐理由的自然语言介绍
4. WHEN 工具返回空结果，THE ResponseGenerator SHALL 生成引导用户换一种描述方式的友好提示
5. THE ResponseGenerator SHALL 保持回复语言与用户输入语言一致（用户说中文则回复中文）
6. IF LLM 生成回复失败，THEN THE ResponseGenerator SHALL 降级为模板回复，确保系统可用性

### 需求 4：Function Calling 工具定义与 ToolOrchestrator 改造

**用户故事：** 作为用户，我希望 Agent 能根据我的描述自主决定调用哪些工具来获取推荐结果，以便得到更精准的个性化推荐。

#### 验收标准

1. THE ToolOrchestrator SHALL 定义以下工具的 JSON Schema：`search_content`（关键词搜索）、`get_similar_content`（相似内容推荐）、`get_user_preference`（获取用户偏好）、`get_content_detail`（查询影视详情）
2. WHEN 用户表达推荐意图，THE ToolOrchestrator SHALL 将工具 schema 和对话上下文传给 LLM，由 LLM 决定调用哪个工具及传入什么参数
3. WHEN LLM 返回 Function Calling 决策，THE ToolOrchestrator SHALL 执行对应的数据库查询并将结果返回给 LLM
4. THE ToolOrchestrator SHALL 支持 LLM 在单次对话中连续调用多个工具（多步推理）
5. WHEN LLM 决定调用 `search_content` 工具，THE ToolOrchestrator SHALL 接受 `query`（查询词）、`content_type`（movie/series）、`genres`（类型列表）、`limit`（返回数量）参数
6. WHEN LLM 决定调用 `get_similar_content` 工具，THE ToolOrchestrator SHALL 接受 `content_title`（参考影视名称）、`limit` 参数，返回相似内容列表
7. IF 工具执行过程中发生数据库错误，THEN THE ToolOrchestrator SHALL 返回包含错误描述的结构化结果，不中断整个对话流程
8. THE ToolOrchestrator SHALL 不再使用基于 intent 字符串的 if-elif 分支逻辑，改为 LLM 驱动的工具调用模式

### 需求 5：多轮对话记忆

**用户故事：** 作为用户，我希望 Agent 能记住本次对话中我说过的内容，以便在多轮对话中不需要重复描述我的偏好。

#### 验收标准

1. THE `/api/agent/chat` 接口 SHALL 接受 `session_id` 参数，用于标识一次对话会话
2. WHEN 用户发送消息时携带 `session_id`，THE 系统 SHALL 将该 session 的历史对话记录追加到传给 LLM 的 `messages` 列表中
3. THE 系统 SHALL 使用内存字典（或 Redis）存储每个 session 的对话历史，格式为 `[{"role": "user"/"assistant", "content": "..."}]` 列表
4. THE 系统 SHALL 对传入 LLM 的历史消息实施滑动窗口控制，默认保留最近 10 轮对话，避免超出 token 限制
5. WHEN 用户在同一 session 中先说"推荐科幻电影"再说"换几部"，THE 系统 SHALL 理解"换几部"是在上一轮推荐基础上的继续请求
6. WHEN `session_id` 不存在时，THE 系统 SHALL 自动创建新的 session 并返回 `session_id` 给前端
7. THE 系统 SHALL 支持 session 过期机制，内存存储默认 30 分钟无活动后清除
8. IF `session_id` 对应的 session 已过期，THEN THE 系统 SHALL 创建新 session 并继续处理请求，不返回错误

### 需求 6：RAG 语义向量检索

**用户故事：** 作为用户，我希望能用"温暖治愈"、"烧脑悬疑"等情感描述来搜索影视内容，以便找到符合我当前心情的作品。

#### 验收标准

1. THE 系统 SHALL 在 PostgreSQL 中安装 pgvector 扩展，并为 `content_items` 表添加 `embedding` 向量列（维度与所选 Embedding 模型一致）
2. THE 系统 SHALL 使用 DeepSeek 或 OpenAI Embedding API 为每条影视记录生成向量，向量化内容为 `title + plot + genres` 的拼接文本
3. THE RagEngine SHALL 提供 `semantic_search(query: str, top_k: int) -> list` 方法，将查询文本向量化后在 pgvector 中执行近邻检索
4. WHEN 用户输入"温暖治愈的电影"，THE RagEngine SHALL 返回语义相似度最高的影视列表，而非仅依赖关键词匹配
5. THE ToolOrchestrator SHALL 新增 `semantic_search` 工具，LLM 可在 Function Calling 中调用该工具处理情感/语义类查询
6. THE RagEngine SHALL 不再依赖本地 `movies.json` 文件，改为从 PostgreSQL `content_items` 表读取数据
7. THE `rag/embedding.py` SHALL 不再使用自制 TF-IDF，改为调用外部 Embedding API
8. IF Embedding API 调用失败，THEN THE 系统 SHALL 降级为关键词全文检索，确保搜索功能可用
9. THE 系统 SHALL 提供批量生成 embedding 的脚本，支持对已有 1233 条影视数据一次性生成向量
10. FOR ALL 影视记录，WHEN 向量化后再执行语义检索，THE 系统 SHALL 能检索到该记录本身（自检索一致性）

### 需求 7：推荐可解释性

**用户故事：** 作为用户，我希望 Agent 能告诉我为什么推荐某部影视，以便我更好地判断是否符合我的口味。

#### 验收标准

1. THE ExplanationGenerator SHALL 被接入 AgentManager 主流程，在生成推荐结果后自动为每条结果生成推荐理由
2. THE ExplanationGenerator SHALL 调用 LLM 生成个性化推荐理由，结合用户偏好历史（genres、directors、actors）和影视内容信息
3. WHEN 工具返回推荐结果列表，THE 系统 SHALL 在每个结果对象中添加 `explanation` 字段，包含该条推荐的个性化理由文本
4. WHEN 用户有明确的偏好历史，THE ExplanationGenerator SHALL 在推荐理由中引用具体的偏好信息（如"因为您喜欢科幻类型"）
5. WHEN 用户无偏好历史（冷启动），THE ExplanationGenerator SHALL 基于影视内容本身的特点生成通用推荐理由
6. THE 前端 `RecommendationCard` 组件 SHALL 展示 `explanation` 字段内容，显示在影视卡片的推荐理由区域
7. IF ExplanationGenerator 调用 LLM 失败，THEN THE 系统 SHALL 使用模板字符串作为降级推荐理由，不影响推荐结果的正常返回

### 需求 8：流式输出（SSE）

**用户故事：** 作为用户，我希望 Agent 的回复能逐字显示，以便在等待完整回复时有更好的交互体验。

#### 验收标准

1. THE `/api/agent/chat` 接口 SHALL 支持 SSE（Server-Sent Events）流式输出模式，通过请求参数 `stream=true` 启用
2. WHEN `stream=true`，THE 系统 SHALL 使用 `text/event-stream` Content-Type 返回响应，逐 token 推送 LLM 生成的文本
3. THE 前端 `ChatBubble` 组件 SHALL 支持接收 SSE 流，实现逐字显示效果
4. WHEN 流式输出完成，THE 系统 SHALL 发送 `[DONE]` 事件标记流结束
5. IF 流式输出过程中发生错误，THEN THE 系统 SHALL 发送包含错误信息的 SSE 事件，前端显示错误提示
6. WHEN `stream=false`（默认），THE 接口 SHALL 保持原有的同步 JSON 响应格式，确保向后兼容

