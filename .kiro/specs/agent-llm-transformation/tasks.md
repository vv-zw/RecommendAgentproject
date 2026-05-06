# 实现任务列表：agent-llm-transformation

## 任务

- [x] 0. 代码清理与项目结构整理
  - [x] 0.1 删除 mock_recommenders/ 目录（ncf.py, textcnn.py, rule_based.py, __init__.py）
  - [x] 0.2 删除 orchestrator/ 目录（recommendation_orchestrator.py, fusion.py, filter.py, score_engine.py）
  - [x] 0.3 删除 agent/intent_parser.py 和 agent/strategy_selector.py
  - [x] 0.4 清理 ai_config/settings.py，删除 FUSION_WEIGHTS 相关配置，保留有效配置项
  - [x] 0.5 删除旧 movie_recommendation/ 中的废弃文件（NeuralCollaborativeFiltering.py, TextCNN.py, app.py, recommendation/ 目录）
  - [x] 0.6 删除临时文件（write_design_part3.py, design_part3.txt, check_users.py, check_crawl_result.py, 安装TensorFlow.bat, 启动应用-Python312.bat）
  - [x] 0.7 验证清理后 api/app.py 可正常启动，无导入错误

- [x] 1. LLM 客户端封装
  - [x] 1.1 新建 ai_config/llm_client.py，实现 get_llm_client()、chat_completion()、get_embedding() 函数
  - [x] 1.2 在 .env.example 中添加 DEEPSEEK_API_KEY、LLM_PROVIDER、LLM_MODEL、EMBEDDING_MODEL 配置项说明
  - [x] 1.3 验证 DeepSeek API 连通性（发送一条测试消息，确认返回正常）

- [x] 2. NLUProcessor 重写
  - [x] 2.1 重写 agent/agent_core/nlu_processor.py，用 LLM + System Prompt 替换英文关键词匹配
  - [x] 2.2 实现 JSON 解析容错：LLM 返回格式不合法时降级返回 intent: unknown
  - [x] 2.3 测试中文意图识别：验证"推荐科幻电影"→ recommend_movie，"有没有类似流浪地球的"→ recommend_movie + keywords

- [x] 3. SessionManager 新建
  - [x] 3.1 新建 agent/session_manager.py，实现 get_or_create()、append()、get_windowed_history()、cleanup_expired()
  - [x] 3.2 实现滑动窗口：默认保留最近 10 轮（20 条消息），System Prompt 不计入窗口
  - [x] 3.3 实现 30 分钟过期清理机制

- [x] 4. ToolOrchestrator 重写（Function Calling）
  - [x] 4.1 重写 agent/agent_core/tool_orchestrator.py，定义 TOOLS_SCHEMA（5 个工具的完整 JSON Schema）
  - [x] 4.2 实现 Function Calling 循环：最多 5 次迭代，解析 tool_calls 并执行对应工具函数
  - [x] 4.3 实现 _tool_search_content()：SQL ILIKE 多字段查询（title、plot、genres）
  - [x] 4.4 实现 _tool_get_user_preference()：查询 user_preferences 表
  - [x] 4.5 实现 _tool_get_content_detail()：查询单条 content_items 详情
  - [x] 4.6 实现 _tool_get_similar_content()：调用 RagEngine.semantic_search()（RAG 完成前先用关键词搜索占位）
  - [x] 4.7 实现 _tool_semantic_search()：调用 RagEngine.semantic_search()（RAG 完成前先用关键词搜索占位）
  - [x] 4.8 测试 Function Calling：验证 LLM 能正确选择工具并传入参数

- [x] 5. ResponseGenerator 重写
  - [x] 5.1 重写 agent/agent_core/response_generator.py，用 LLM 生成自然语言回复
  - [x] 5.2 实现降级策略：LLM 失败时回退到模板字符串拼接
  - [x] 5.3 支持 stream=True 时返回 token 生成器

- [x] 6. AgentManager 重构 + API 路由扩展
  - [x] 6.1 重构 agent/recommendation_agent.py，接入 SessionManager，协调 NLU → ToolOrchestrator → ResponseGenerator 新流程
  - [x] 6.2 扩展 api/routes.py 的 /api/agent/chat 接口，新增 session_id 参数，返回值中包含 session_id
  - [x] 6.3 端到端测试：发送中文消息，验证完整链路（NLU → Function Calling → LLM 回复）正常工作

- [x] 7. 多轮对话验证
  - [x] 7.1 测试同一 session 多轮对话：先说"推荐科幻电影"，再说"换几部"，验证上下文连贯
  - [x] 7.2 测试 session 过期：30 分钟后发送消息，验证自动创建新 session

- [-] 8. RAG 语义向量检索
  - [-] 8.1 在 PostgreSQL 中安装 pgvector 扩展（CREATE EXTENSION vector）
  - [ ] 8.2 为 content_items 表添加 embedding 向量列（ALTER TABLE ADD COLUMN embedding vector(1536)）
  - [x] 8.3 重写 rag/embedding.py，改为调用 DeepSeek/OpenAI Embedding API
  - [x] 8.4 重写 rag/rag_engine.py，实现 semantic_search()、index_content()、batch_index()
  - [ ] 8.5 编写批量向量化脚本，为已有 1233 条影视数据生成 embedding
  - [ ] 8.6 将 ToolOrchestrator 中的 _tool_semantic_search() 和 _tool_get_similar_content() 切换为真实 pgvector 检索
  - [ ] 8.7 测试语义检索：验证"温暖治愈的电影"能返回相关结果

- [x] 9. 推荐可解释性
  - [x] 9.1 重写 explain/explanation_generator.py，用 LLM 生成个性化推荐理由
  - [x] 9.2 在 AgentManager 主流程中接入 ExplanationGenerator，为每条推荐结果添加 explanation 字段
  - [x] 9.3 更新前端 RecommendationCard 组件，展示 explanation 字段内容
  - [x] 9.4 实现降级策略：LLM 失败时使用模板字符串

- [x] 10. 流式输出（SSE）
  - [x] 10.1 扩展 /api/agent/chat 接口，支持 stream=true 参数，返回 text/event-stream
  - [x] 10.2 实现 SSE 事件格式：逐 token 推送，结束时发送 [DONE]
  - [x] 10.3 更新前端 agentApi.chat() 和 ChatBubble 组件，支持 SSE 流式接收和逐字显示
  - [x] 10.4 测试流式输出：验证前端逐字显示效果正常
