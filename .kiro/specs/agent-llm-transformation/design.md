# 技术设计文档：Agent LLM 改造

## 概述

本文档描述将现有影视推荐系统的 Agent 模块从基于规则的实现升级为 LLM 驱动的智能推荐助手的技术方案。

**改造背景**：当前 NLUProcessor 仅识别英文关键词，ToolOrchestrator 直接执行硬编码 SQL，ResponseGenerator 拼接模板字符串，RAG 模块依赖本地 JSON + 自制 TF-IDF。整个 Agent 链路没有接入任何真实 LLM，无法处理中文输入，也不具备多轮对话能力。

**改造目标**：以 DeepSeek API 为核心，通过 Function Calling 驱动工具调用，结合 pgvector 语义检索和 SSE 流式输出，构建真正的 LLM 驱动推荐助手。

改造范围涵盖六个核心方向：

1. **LLM 接入**：封装 DeepSeek API 客户端，统一管理 API Key 和模型参数
2. **NLU 改造**：用 LLM + System Prompt 替换英文关键词匹配，支持中文意图理解
3. **Function Calling**：定义工具 JSON Schema，由 LLM 自主决策工具调用
4. **多轮对话记忆**：内存字典 + 滑动窗口管理 session 历史
5. **RAG 向量检索**：pgvector + Embedding API 替换本地 TF-IDF
6. **流式输出**：SSE 实现逐 token 推送

## 架构

### 改造后的 Agent 调用链

\\mermaid
flowchart TD
    U([用户输入]) --> API[/api/agent/chat Flask Route]
    API --> SM[SessionManager 读取/写入对话历史]
    SM --> AM[AgentManager process_user_request]
    AM --> NLU[NLUProcessor LLM意图理解]
    NLU -->|intent + entities| FC[ToolOrchestrator Function Calling Loop]
    FC -->|tools schema + messages| LLM[(DeepSeek LLM deepseek-chat)]
    LLM -->|tool_call 决策| FC
    FC --> T1[search_content SQL ILIKE查询]
    FC --> T2[get_similar_content RAG语义检索]
    FC --> T3[get_user_preference 查询用户偏好表]
    FC --> T4[get_content_detail 查询影视详情]
    FC --> T5[semantic_search pgvector近邻检索]
    T1 & T2 & T3 & T4 & T5 --> DB[(PostgreSQL content_items + pgvector)]
    FC -->|tool results| RG[ResponseGenerator LLM自然语言生成]
    RG --> EG[ExplanationGenerator 推荐理由生成]
    EG --> SM2[SessionManager 追加assistant消息]
    SM2 --> OUT([JSON响应 / SSE流])
\
### 模块职责划分

| 模块 | 文件 | 改造方式 | 职责 |
|---|---|---|---|
| LLM 客户端 | ai_config/llm_client.py（新建） | 全新实现 | 封装 DeepSeek/OpenAI 调用，统一错误处理 |
| 配置管理 | ai_config/settings.py | 重构 | 读取 API Key、Provider、模型参数，删除废弃融合权重 |
| NLU 处理器 | agent/agent_core/nlu_processor.py | 重写 | LLM 驱动的中文意图理解 |
| 工具编排器 | agent/agent_core/tool_orchestrator.py | 重写 | Function Calling 循环，工具 schema 定义 |
| 响应生成器 | agent/agent_core/response_generator.py | 重写 | LLM 生成自然语言回复 |
| Agent 主入口 | agent/recommendation_agent.py | 重构 | 接入 session 管理，协调各组件 |
| Session 管理 | agent/session_manager.py（新建） | 全新实现 | 内存字典 + 滑动窗口 |
| RAG 引擎 | rag/rag_engine.py | 重写 | pgvector 语义检索 |
| Embedding | rag/embedding.py | 重写 | 调用 Embedding API |
| 解释生成器 | explain/explanation_generator.py | 重写 | LLM 生成个性化推荐理由 |
| API 路由 | api/routes.py | 扩展 | 新增 session_id、stream 参数支持 |

