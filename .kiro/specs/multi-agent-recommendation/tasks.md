# 实现计划：多 Agent 协作推荐架构

## 概述

本计划将现有单一 AgentManager 架构重构为多 Agent 协作架构，引入 RouterAgent、AnalysisAgent、RecommendationAgent、ExplanationAgent、ChitchatAgent 五个职责单一的 Agent，通过 AgentOrchestrator 统一编排。实现语言：Python。

## 任务

- [ ] 1. 创建 agents 子包并定义 StructuredContext 数据类
  - 在 `agent/agents/` 目录下创建 `__init__.py`
  - 在 `agent/agents/structured_context.py` 中定义 `StructuredContext` dataclass，包含 `intent`、`confidence`、`mood`、`genres`、`keywords`、`directors`、`actors`、`content_type`、`context`、`skip_preference_injection`、`clarify_question`、`clarify_round` 字段
  - 为所有字段设置合理的默认值，确保可以无参数实例化
  - _需求：2.6、6.1_

- [ ] 2. 实现 RouterAgent（意图分类）
  - [ ] 2.1 创建 `agent/agents/router_agent.py`，实现 `RouterAgent` 类
    - 实现 `route(self, user_message: str, history: list) -> str` 方法
    - 使用设计文档中的 System Prompt，temperature=0.2
    - 返回值严格为四种意图类型之一：`explicit_query`、`vague_recommendation`、`mixed`、`chitchat`
    - LLM 调用失败时降级返回 `vague_recommendation`
    - _需求：1.1、1.6、1.7_

  - [ ]* 2.2 为 RouterAgent 编写单元测试
    - 测试四种意图类型的正确分类
    - 测试 LLM 调用失败时的降级行为
    - _需求：1.1、1.7_

- [ ] 3. 实现 AnalysisAgent（需求分析与追问）
  - [ ] 3.1 创建 `agent/agents/analysis_agent.py`，实现 `AnalysisAgent` 类
    - 实现 `analyze(self, user_message: str, history: list, clarify_round: int = 0) -> StructuredContext` 方法
    - 使用设计文档中的 System Prompt，解析 LLM 返回的 JSON 为 StructuredContext
    - 当 `clarify_round >= 3` 时，在 prompt 中注入强制输出指令，确保 `clarify_question` 为空
    - LLM 调用失败时，用原始输入构造最小化 StructuredContext，`confidence=low`，`clarify_question` 为空
    - _需求：2.1、2.2、2.3、2.4、2.5、2.6、2.7_

  - [ ]* 3.2 为 AnalysisAgent 编写单元测试
    - 测试 `confidence=high` 时不生成追问
    - 测试 `confidence=low` 时生成追问
    - 测试 `clarify_round=3` 时强制输出不追问
    - 测试 LLM 失败时的降级行为
    - _需求：2.2、2.3、2.5、2.7_

- [ ] 4. 实现 RecommendationAgent（动态策略 + Function Calling）
  - [ ] 4.1 创建 `agent/agents/recommendation_agent.py`，实现 `RecommendationAgent` 类
    - 实现 `execute(self, user_id: str, ctx: StructuredContext, preference_context: Optional[dict], messages: list) -> list[dict]` 方法
    - 复用 `agent/agent_core/tool_orchestrator.py` 中的工具实现（`_tool_search_content`、`_tool_semantic_search` 等）
    - 在现有 `TOOLS_SCHEMA` 的 `search_content` 工具中新增 `sort_by` 参数（`rating`、`popularity`、`relevance`）
    - _需求：3.1、3.5、3.6_

  - [ ] 4.2 实现 explicit_query 推荐策略
    - 当 `ctx.skip_preference_injection=True` 时，System Prompt 中明确禁止调用 `get_user_preference` 工具
    - `search_content` 调用时优先使用 `sort_by=rating` 或 `sort_by=popularity`
    - _需求：3.1、3.2_

  - [ ] 4.3 实现 vague_recommendation 个性化推荐策略
    - 当 `ctx.skip_preference_injection=False` 且 `confidence=high` 时，优先调用 `get_user_preference` 并以偏好为主要过滤条件
    - 当 `confidence=medium` 或 `low` 时，同时执行偏好检索和通用检索，合并去重
    - _需求：3.3、3.4_

  - [ ] 4.4 实现兜底查询逻辑
    - 当所有工具调用均返回空结果时，执行无过滤条件的全库热门内容兜底查询（`ORDER BY popularity DESC LIMIT 10`）
    - _需求：3.7_

  - [ ] 4.5 实现 generate_response 方法
    - 实现 `generate_response(self, results: list[dict], ctx: StructuredContext, stream: bool = False) -> str | Generator` 方法
    - 复用现有 `ResponseGenerator` 的生成逻辑，支持流式和非流式输出
    - _需求：6.3_

  - [ ]* 4.6 为 RecommendationAgent 编写单元测试
    - 测试 `skip_preference_injection=True` 时不调用 `get_user_preference`
    - 测试兜底查询在所有工具返回空时触发
    - _需求：3.1、3.7_

- [ ] 5. 检查点 - 确保所有已实现的 Agent 单元测试通过
  - 确保所有测试通过，如有问题请向用户反馈。

- [ ] 6. 实现 ExplanationAgent（包装现有 ExplanationGenerator）
  - [ ] 6.1 创建 `agent/agents/explanation_agent.py`，实现 `ExplanationAgent` 类
    - 实现 `explain(self, results: list[dict], ctx: StructuredContext) -> list[dict]` 方法
    - 包装 `explain/explanation_generator.py` 中的 `ExplanationGenerator`
    - 在调用 LLM 时，将 `ctx.mood` 和 `ctx.context` 注入 System Prompt（使用设计文档中的改进版 Prompt）
    - LLM 失败时调用现有 `ExplanationGenerator._template_explanation` 降级
    - _需求：4.1、4.2、4.3、4.4、4.5、4.6_

  - [ ]* 6.2 为 ExplanationAgent 编写单元测试
    - 测试 `mood` 非空时推荐理由包含情绪维度
    - 测试 `context` 非空时推荐理由包含场景信息
    - 测试 LLM 失败时降级为模板理由
    - _需求：4.2、4.3、4.5_

- [ ] 7. 实现 ChitchatAgent（提取现有闲聊逻辑）
  - [ ] 7.1 创建 `agent/agents/chitchat_agent.py`，实现 `ChitchatAgent` 类
    - 实现 `chat(self, message: str, history: list) -> str` 方法
    - 将现有 `AgentManager._handle_chitchat` 的逻辑迁移至此，使用设计文档中的 System Prompt
    - 回复长度不超过 150 字，不调用任何推荐工具
    - LLM 失败时返回固定友好提示语
    - _需求：5.1、5.2、5.3、5.4_

  - [ ]* 7.2 为 ChitchatAgent 编写单元测试
    - 测试正常闲聊回复不超过 150 字
    - 测试 LLM 失败时返回固定提示语
    - _需求：5.1、5.4_

- [ ] 8. 实现 AgentOrchestrator（统一编排）
  - [ ] 8.1 创建 `agent/orchestrator.py`，实现 `AgentOrchestrator` 类
    - 在 `__init__` 中初始化所有五个 Agent 实例
    - 实现 `process_user_request(self, user_id, user_message, preference_context, session_id, stream)` 方法，签名与现有 `AgentManager.process_user_request` 完全一致
    - 返回值类型保持 `tuple[str | Generator, list, str]`
    - _需求：6.1、7.1_

  - [ ] 8.2 实现编排主流程
    - 调用 `session_manager.get_or_create(session_id)` 获取历史
    - 调用 `RouterAgent.route()` 获取意图类型
    - 根据意图类型分发：`chitchat` -> ChitchatAgent，`explicit_query` -> 直接构造 StructuredContext 进入推荐，`vague_recommendation`/`mixed` -> AnalysisAgent
    - _需求：6.2、1.2、1.3、1.4、1.5_

  - [ ] 8.3 实现 Session 追问轮次管理
    - 在 `_sessions[session_id]` 中维护 `clarify_round` 字段（整数，默认 0）
    - 当 AnalysisAgent 返回非空 `clarify_question` 时，将追问消息以 `role=assistant` 写入 session，`clarify_round` 加 1，返回 `(clarify_question, [], session_id)`
    - 当 Router 返回非 `chitchat` 且上一条 assistant 消息不是追问时，重置 `clarify_round=0`
    - _需求：2.4、2.5、6.4、6.5_

  - [ ] 8.4 实现推荐与解释链路
    - AnalysisAgent 返回 `confidence=high` 或追问轮次达到 3 时，调用 `RecommendationAgent.execute()` 获取结果
    - 调用 `RecommendationAgent.generate_response()` 生成自然语言回复（支持 stream）
    - 调用 `ExplanationAgent.explain()` 为结果添加推荐理由
    - 写入 session 历史，返回 `(nl_response, results, session_id)`
    - _需求：6.2、6.3、6.4_

  - [ ] 8.5 实现异常处理与错误日志
    - 用 try/except 包裹整个编排流程
    - 捕获任意 Agent 抛出的未捕获异常，记录 `logger.error` 日志
    - 返回友好错误提示，不向前端暴露内部异常信息
    - _需求：6.6_

  - [ ]* 8.6 为 AgentOrchestrator 编写集成测试
    - 测试 `chitchat` 意图路径：返回 `structured_results=[]`
    - 测试 `explicit_query` 意图路径：不经过 AnalysisAgent
    - 测试追问轮次管理：`clarify_round` 正确递增和重置
    - 测试异常时返回友好错误提示
    - _需求：6.1、6.2、6.5、6.6_

- [ ] 9. 修改 api/routes.py 导入
  - 将 `api/routes.py` 中 `chat` 路由函数内的导入语句从 `from agent.recommendation_agent import AgentManager` 改为 `from agent.orchestrator import AgentOrchestrator`
  - 将 `agent = AgentManager()` 改为 `agent = AgentOrchestrator()`
  - 不修改路由函数签名、请求/响应字段、SSE 事件格式
  - _需求：7.1、7.2、7.3、7.4、7.5_

- [ ] 10. 检查点 - 端到端验证
  - 确保所有单元测试和集成测试通过
  - 验证非流式响应字段：`nl_response`、`structured_results`、`session_id` 均存在
  - 验证 SSE 流式响应事件格式：`meta` 事件含 `session_id` 和 `structured_results`，`token` 事件含 `content`，结束标记为 `[DONE]`
  - 验证追问轮次场景：`structured_results` 为空列表，`nl_response` 为追问文本
  - 如有问题请向用户反馈。

## 备注

- 标有 `*` 的子任务为可选测试任务，可跳过以加快 MVP 交付
- 每个任务均引用了具体需求条款，确保可追溯性
- 任务 1-4 可并行开发（各 Agent 相互独立），任务 8 依赖 1-7 全部完成
- 任务 9 是最后一步，确保所有 Agent 验证通过后再修改路由导入
- 现有 `agent/agent_core/tool_orchestrator.py`、`explain/explanation_generator.py`、`agent/session_manager.py` 均不修改，仅被新 Agent 复用