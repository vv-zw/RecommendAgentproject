# 实施计划：多 Agent 协作推荐架构

## 任务重述

将现有影视推荐系统的单一 `AgentManager`（线性链路：NLUProcessor → ToolOrchestrator → ResponseGenerator）升级为多 Agent 协作架构，引入 5 个职责单一的 Agent（Router、Analysis、Recommendation、Explanation、Chitchat），通过 `AgentOrchestrator` 统一编排，在保持 API 向后兼容的前提下解决 NLU 被动解析和推荐策略单一两个核心痛点。

## 当前状态分析

- **现有架构**：`AgentManager` 在 `agent/recommendation_agent.py` 中，内部依次调用 `NLUProcessor`、`ToolOrchestrator`、`ResponseGenerator`，最后调用 `ExplanationGenerator`
- **API 层**：`api/routes.py` 的 `/api/agent/chat` 端点直接实例化 `AgentManager` 并调用 `process_user_request`
- **Session 管理**：`SessionManager` 使用进程内字典存储，30 分钟 TTL
- **LLM 客户端**：`ai_config/llm_client.py` 提供 `chat_completion` 统一入口，支持 Function Calling
- **工具集**：`ToolOrchestrator` 定义了 5 个工具（search_content、semantic_search、get_similar_content、get_user_preference、get_content_detail）
- **需要复用不修改的模块**：`session_manager.py`、`llm_client.py`、`explanation_generator.py`、`tool_orchestrator.py`（被 RecommendationAgent 内部复用）

## 实施步骤

### 步骤 1：创建 agents 子包并定义 StructuredContext 数据类

- **文件**：`agent/agents/__init__.py`（新建）、`agent/agents/structured_context.py`（新建）
- **内容**：
  - `__init__.py`：导出所有 Agent 类和 StructuredContext
  - `structured_context.py`：定义 `StructuredContext` dataclass，包含 `intent`、`confidence`、`mood`、`genres`、`keywords`、`directors`、`actors`、`content_type`、`context`、`skip_preference_injection`、`clarify_question`、`clarify_round` 字段，所有字段设置合理默认值
- **原因**：StructuredContext 是贯穿整个 Agent 链路的核心数据结构，必须首先定义

### 步骤 2：实现 RouterAgent（意图分类）

- **文件**：`agent/agents/router_agent.py`（新建）
- **内容**：
  - 实现 `RouterAgent` 类，`route(user_message, history) -> str` 方法
  - 使用设计文档中的 System Prompt，`temperature=0.2`
  - 返回四种意图类型之一：`explicit_query`、`vague_recommendation`、`mixed`、`chitchat`
  - LLM 调用失败时降级返回 `vague_recommendation`
  - 对 LLM 返回做清洗，提取有效意图类型词
- **原因**：Router 是整个链路的入口，必须先实现

### 步骤 3：实现 AnalysisAgent（需求分析与追问）

- **文件**：`agent/agents/analysis_agent.py`（新建）
- **内容**：
  - 实现 `AnalysisAgent` 类，`analyze(user_message, history, clarify_round=0) -> StructuredContext` 方法
  - 使用设计文档中的 System Prompt，解析 LLM 返回的 JSON 为 StructuredContext
  - `clarify_round >= 3` 时在 prompt 中注入强制输出指令
  - LLM 失败时用原始输入构造最小化 StructuredContext，`confidence=low`
  - JSON 解析失败时做容错处理
- **原因**：AnalysisAgent 处理模糊推荐场景的核心追问逻辑

### 步骤 4：实现 RecommendationAgent（动态策略 + Function Calling）

- **文件**：`agent/agents/recommendation_agent.py`（新建）
- **内容**：
  - 实现 `RecommendationAgent` 类，包含 `execute()` 和 `generate_response()` 两个方法
  - `execute()`：复用 `ToolOrchestrator` 的工具实现，根据 `ctx.skip_preference_injection` 动态调整 System Prompt 和工具调用策略
  - 在 `search_content` 工具 schema 中新增 `sort_by` 参数
  - `generate_response()`：复用 `ResponseGenerator` 的生成逻辑，支持流式和非流式
  - 实现兜底查询：所有工具返回空时执行全库热门查询
  - `skip_preference_injection=True` 时禁止调用 `get_user_preference`，偏好权重不超过 20%
  - `skip_preference_injection=False` 时根据 confidence 选择策略（high=偏好优先，medium/low=合并去重）
- **原因**：RecommendationAgent 是推荐核心，整合了现有 ToolOrchestrator 和 ResponseGenerator 的功能
- **依赖**：需要复用 `agent/agent_core/tool_orchestrator.py` 中的工具实现

### 步骤 5：实现 ExplanationAgent（包装现有 ExplanationGenerator）

- **文件**：`agent/agents/explanation_agent.py`（新建）
- **内容**：
  - 实现 `ExplanationAgent` 类，`explain(results, ctx) -> list[dict]` 方法
  - 包装 `explain/explanation_generator.py` 中的 `ExplanationGenerator`
  - 将 `ctx.mood` 和 `ctx.context` 注入 LLM Prompt
  - LLM 失败时调用现有 `_template_explanation` 降级
- **原因**：ExplanationAgent 在现有基础上增加 mood/context 感知能力

### 步骤 6：实现 ChitchatAgent（提取现有闲聊逻辑）

- **文件**：`agent/agents/chitchat_agent.py`（新建）
- **内容**：
  - 实现 `ChitchatAgent` 类，`chat(message, history) -> str` 方法
  - 迁移现有 `AgentManager._handle_chitchat` 的逻辑
  - 使用设计文档中的 System Prompt，回复不超过 150 字
  - LLM 失败时返回固定友好提示语
- **原因**：将闲聊处理独立为单独 Agent

### 步骤 7：实现 AgentOrchestrator（统一编排）

- **文件**：`agent/orchestrator.py`（新建）
- **内容**：
  - 实现 `AgentOrchestrator` 类，`process_user_request()` 签名与现有 `AgentManager` 完全一致
  - 编排主流程：Router → Analysis（条件触发）→ Recommendation → Explanation
  - Session 追问轮次管理：在 session 中维护 `clarify_round`，追问时递增，新请求时重置
  - 追问轮次返回 `(clarify_question, [], session_id)`
  - 流式支持：透传 RecommendationAgent 的流式输出
  - 异常处理：try/except 包裹，记录日志，返回友好错误提示
- **原因**：Orchestrator 是替换 AgentManager 的核心入口，依赖所有其他 Agent

### 步骤 8：修改 api/routes.py 导入

- **文件**：`api/routes.py`（修改）
- **内容**：
  - 将 `from agent.recommendation_agent import AgentManager` 改为 `from agent.orchestrator import AgentOrchestrator`
  - 将 `agent = AgentManager()` 改为 `agent = AgentOrchestrator()`
  - 不修改路由函数签名、请求/响应字段、SSE 事件格式
- **原因**：确保 API 向后兼容，前端无需修改

### 步骤 9：更新 agent/recommendation_agent.py 向后兼容

- **文件**：`agent/recommendation_agent.py`（修改）
- **内容**：
  - 保留 `AgentManager` 类名和 `process_user_request` 方法签名
  - 内部改为导入并委托给 `AgentOrchestrator`
  - 确保其他可能引用 `AgentManager` 的代码不会中断
- **原因**：设计文档要求保留该文件以向后兼容

### 步骤 10：验证

- 运行现有测试确保无回归
- 验证非流式响应字段完整性
- 验证 SSE 流式响应事件格式
- 验证追问轮次场景
- 验证各 Agent 降级策略

## 假设与决策

1. **测试策略**：tasks.md 中标有 `*` 的子任务为可选测试任务，本次实施优先完成核心功能代码，测试作为验证步骤
2. **SessionManager 不修改**：直接复用现有实现，`clarify_round` 通过在 session 字典中新增字段实现
3. **ToolOrchestrator 不修改**：RecommendationAgent 内部复用其工具实现，通过组合而非继承的方式集成
4. **ResponseGenerator 不修改**：RecommendationAgent 的 `generate_response` 方法内部调用现有 ResponseGenerator
5. **ExplanationGenerator 不修改**：ExplanationAgent 包装调用现有实现
6. **LLM 客户端不修改**：所有新 Agent 复用现有 `chat_completion` 函数
7. **search_content 的 sort_by 参数**：在 RecommendationAgent 内部处理，不修改原始 ToolOrchestrator 的 TOOLS_SCHEMA

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新建 | `agent/agents/__init__.py` | agents 子包初始化 |
| 新建 | `agent/agents/structured_context.py` | StructuredContext 数据类 |
| 新建 | `agent/agents/router_agent.py` | RouterAgent |
| 新建 | `agent/agents/analysis_agent.py` | AnalysisAgent |
| 新建 | `agent/agents/recommendation_agent.py` | RecommendationAgent |
| 新建 | `agent/agents/explanation_agent.py` | ExplanationAgent |
| 新建 | `agent/agents/chitchat_agent.py` | ChitchatAgent |
| 新建 | `agent/orchestrator.py` | AgentOrchestrator |
| 修改 | `api/routes.py` | 仅修改导入语句 |
| 修改 | `agent/recommendation_agent.py` | 委托给 AgentOrchestrator |
