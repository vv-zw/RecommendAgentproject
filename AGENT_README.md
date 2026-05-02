# Recommendation Agent

## 1. Agent 作用 (Agent's Purpose)

Recommendation Agent 是一个前置处理模块，设计用于在主推荐系统之前运行。其主要职责是理解用户的请求，并决定*如何*生成推荐，而不是实际执行推荐。

该代理将决策逻辑与核心推荐算法解耦，从而可以在不修改现有推荐服务的情况下实现灵活的策略选择。

核心功能:
- **意图识别**: 判断用户是想要推荐、搜索还是解释。
- **特征提取**: 从用户的查询中提取电影名称或类型等关键信息。
- **策略选择**: 根据用户的意图、查询和上下文（如用户历史记录），决定应调用哪些下游模型（例如，NCF、TextCNN、规则）。

代理的最终输出是一个结构化的JSON对象，其中包含此策略决策，然后可由后续模块使用以执行实际的推荐。

## 2. 输入输出格式 (Input/Output Format)

### 输入 (Input)

代理需要一个具有以下结构的JSON对象：

```json
{
  "user_id": 1,
  "query": "推荐类似流浪地球的电影",
  "context": {
    "device": "web",
    "history": [123, 456]
  }
}
```
- `user_id`: 用户的唯一标识符。
- `query`: 用户的自然语言请求。
- `context`: 包含附加信息。
  - `history`: 代表用户交互历史的项目ID列表。空列表 `[]` 表示冷启动用户。

### 输出 (Output)

代理生成一个标准化的JSON对象，详细说明要使用的策略：

```json
{
  "intent": "recommend",
  "keywords": ["流浪地球"],
  "genres": ["科幻"],
  "mood": null,
  "strategy": {
    "use_ncf": true,
    "use_textcnn": true,
    "use_rules": true,
    "use_rag": false
  },
  "explain_required": true
}
```
- `intent`: 识别出的用户意图。
- `keywords`, `genres`, `mood`: 从查询中提取的特征。
- `strategy`: 一组布尔值，指示要使用哪些推荐模型。
  - `use_ncf`: 协同过滤模型。对冷启动用户禁用。
  - `use_textcnn`: 语义匹配模型。
  - `use_rules`: 基于规则的推荐模型。
  - `use_rag`: 检索增强生成（在此阶段始终为 `false`）。
- `explain_required`: 一个布尔值，指示最终推荐是否应附带解释。

## 3. 如何接入现有系统 (How to Integrate with an Existing System)

该代理被设计为一个轻量级的即插即用模块。

### 运行和测试 (Running and Testing)

代理模块可以直接从命令行进行测试。这将运行预定义的测试用例。

首先，确保您的目录结构如下：
```
d:\RecommendAgentProject\
|-- agent\
|   |-- __init__.py (可以是空文件)
|   |-- intent_parser.py
|   |-- recommendation_agent.py
|   |-- strategy_selector.py
|-- AGENT_README.md
```

然后从根目录 (`d:\RecommendAgentProject`) 运行以下命令:

```bash
python -m agent.recommendation_agent
```

运行后，您将看到3个测试用例的输入和格式化的JSON输出。

*注意: 为了让 `from agent...` 导入正常工作，您可能需要在 `agent` 文件夹中创建一个空的 `__init__.py` 文件。*

### 集成步骤 (Integration Steps)

1.  **实例化代理**: 在您现有的应用程序（例如Flask或FastAPI后端）中，导入并创建代理的实例。

    ```python
    from agent.recommendation_agent import RecommendationAgent
    
    recommendation_agent = RecommendationAgent()
    ```

2.  **调用代理**: 在处理推荐请求的API端点中，首先使用用户的请求数据调用 `agent.decide()` 方法。

    ```python
    # Flask-like 端点中的示例
    # @app.route('/api/ai/recommend', methods=['POST'])
    def handle_recommendation_request():
        user_request = request.json # 获取用户输入
        
        # 从代理获取策略决策
        strategy_json = recommendation_agent.decide(user_request)
        
        # 现在，使用 strategy_json 调用适当的服务
        # (这部分由流水线中的下一个模块处理)
        
        # 目前，您可以只返回代理的决策
        return jsonify(strategy_json)
    ```

3.  **使用输出**: 下游逻辑（“执行器”模块）将接收来自代理的JSON。然后，它将读取 `strategy` 对象，并根据哪些标志为 `true` 来有条件地调用相应的推荐服务（NCF、TextCNN等）。

这种方法确保了核心推荐系统无需修改。代理充当智能路由器，根据其分析结果引导流量。
