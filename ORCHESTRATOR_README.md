# Recommendation Orchestrator

## 1. Orchestrator 作用 (Module's Purpose)

**Recommendation Orchestrator** 是整个推荐流程的**总调度中心**。它扮演着“指挥官”的角色，负责将 Phase 1 Agent 产生的**决策**转化为实际的推荐动作。

其核心职责是编排、融合和后处理，而不是执行任何核心算法。它连接了决策层（Agent）和执行层（现有的 NCF、TextCNN、Rule 模型），并输出最终的、可供用户消费的推荐列表。

核心功能:
- **流程编排**: 根据 Agent 决策，动态地调用一个或多个推荐模型（NCF、TextCNN、Rule）。
- **结果融合**: 对来自不同模型的推荐结果，根据场景（如冷启动、语义查询）进行动态加权，计算出统一的融合分数。
- **过滤与清洗**: 对融合后的结果进行去重，并移除用户已经看过或不感兴趣的内容。
- **标准化输出**: 生成包含最终推荐列表和调试信息的标准化JSON。

## 2. 数据流说明 (Data Flow)

Orchestrator 的完整数据处理流程如下：

1.  **接收输入**: 接收包含 `user_id`, `query`, 和 `agent_decision` 的请求。
2.  **调度模型**: 解析 `agent_decision.strategy`，并调用 `recommendation/` 目录下的相应（模拟）模型函数。
3.  **获取原始结果**: 每个被调用的模型返回一个独立的候选列表。
4.  **动态加权融合**: `fusion.py` 根据 Agent 决策和查询内容（例如，是否为冷启动）确定各模型结果的权重，并调用 `score_engine.py` 计算出每个电影的最终 `hybrid` 分数。
5.  **过滤清洗**: `filter.py` 移除已看过的电影和重复项。
6.  **排序和截断**: 根据最终分数对列表进行降序排序，并返回 Top-K 个结果。
7.  **输出**: 生成包含 `recommendations` 和 `debug_trace` 的最终JSON。

## 3. 如何运行与调用 (How to Run and Call)

### 独立运行测试 (Standalone Testing)

您可以直接从项目根目录运行 Orchestrator 模块的测试脚本，以验证其完整的编排功能。

```bash
# 确保您在 d:\RecommendAgentProject 目录下
python -m orchestrator.recommendation_orchestrator
```

此命令将执行 `recommendation_orchestrator.py` 中的3个测试用例，模拟从接收 Agent 决策到输出最终推荐列表的全过程。

*注意: 为了让 `from orchestrator...` 和 `from recommendation...` 导入正常工作，您可能需要在 `orchestrator` 和 `recommendation` 文件夹中创建空的 `__init__.py` 文件。*

### 如何接入 Phase 1 Agent

Orchestrator 是 Agent 的直接下游。一个完整的端到端流程如下：

```python
# 在一个完整的API端点中（例如 Flask）
from agent.recommendation_agent import RecommendationAgent
from orchestrator.recommendation_orchestrator import RecommendationOrchestrator

# 1. 初始化
agent = RecommendationAgent()
orchestrator = RecommendationOrchestrator()

# 2. 获取用户原始请求
user_http_request = {"user_id": 1, "query": "推荐类似流浪地球的电影", "context": {"history": [123]}}

# 3. Phase 1: Agent 决策
agent_decision = agent.decide(user_http_request)

# 4. 准备 Orchestrator 输入
orchestrator_input = {
    "user_id": user_http_request["user_id"],
    "query": user_http_request["query"],
    "agent_decision": agent_decision
}

# 5. Phase 3: Orchestrator 执行编排并返回最终结果
final_recommendations = orchestrator.orchestrate(orchestrator_input)

# 6. 返回给用户
# return jsonify(final_recommendations)
```

### 如何调用现有推荐系统

本模块通过从 `recommendation` 包导入函数来调用现有的推荐系统。当前，这些是**模拟函数**。

要切换到您的**真实系统**，您只需：

1.  确保您的真实 `get_ncf_recommendations`, `get_textcnn_recommendations` 等函数可用。
2.  修改 `orchestrator/recommendation_orchestrator.py` 文件顶部的 `import` 语句，使其指向您真实的模块路径。

例如，将：
`from recommendation.ncf import get_ncf_recommendations`

修改为：
`from your_real_system.ncf_engine import get_ncf_recommendations`

只要您的真实函数返回与模拟函数相同格式（一个包含 `movie_id`, `title`, `score` 的字典列表），Orchestrator 的其余部分将无缝工作，无需任何更改。
