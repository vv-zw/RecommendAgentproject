# RAG Semantic Retrieval Module

## 1. RAG 模块作用 (Module's Purpose)

**RAG 语义召回模块** 是一个独立的候选集生成器。它的核心任务是根据用户查询的**文本语义**，从电影库中检索出最相关的一批候选电影。

此模块是推荐系统中的**召回层 (Retrieval Layer)**。它不负责最终的排序或推荐决策，而是为后续的排序模块（Ranker）提供一个高质量、语义相关的候选电影列表。

核心功能:
- **文本向量化**: 使用从零实现的 **TF-IDF** 算法，将用户查询和电影的文本信息（标题 + 描述）转换为向量。
- **语义检索**: 通过计算查询向量与所有电影向量之间的**余弦相似度 (Cosine Similarity)** 来衡量相关性。
- **候选集召回**: 返回与查询语义最相似的 Top-K 个电影作为候选集。

该模块完全独立，不依赖 Agent 或任何其他推荐算法，并且只使用 Python 标准库，无任何外部依赖。

## 2. 输入输出格式 (Input/Output Format)

### 输入 (Input)

模块需要一个具有以下结构的JSON对象：

```json
{
  "query": "推荐类似流浪地球的科幻电影",
  "top_k": 10
}
```
- `query`: 用户的自然语言查询。
- `top_k`: （可选）希望返回的候选集大小，默认为 10。

### 输出 (Output)

模块生成一个标准化的JSON对象，包含查询和召回的候选集：

```json
{
  "query": "推荐类似流浪地球的科幻电影",
  "candidates": [
    {
      "movie_id": 12,
      "title": "星际穿越",
      "score": 0.92
    },
    {
      "movie_id": 8,
      "title": "火星救援",
      "score": 0.88
    }
  ]
}
```
- `query`: 原始的用户查询。
- `candidates`: 一个列表，包含召回的电影。
  - `movie_id`: 电影的唯一标识符。
  - `title`: 电影标题。
  - `score`: 该电影与查询的余弦相似度得分，用于衡量语义相关性。

## 3. 数据依赖说明 (Data Dependency)

本模块依赖一个本地的JSON文件来获取电影信息。

- **文件路径**: `data/datasets/movies.json`
- **文件结构**:
  ```json
  [
    {
      "movie_id": 1,
      "title": "流浪地球",
      "genres": ["科幻"],
      "description": "太阳即将毁灭，人类..."
    }
  ]
  ```
在运行模块之前，请确保此文件存在且路径正确。

## 4. 如何运行与调用 (How to Run and Call)

### 独立运行测试 (Standalone Testing)

您可以直接从项目根目录运行 RAG 模块的测试脚本，以验证其功能。

```bash
# 确保您在 d:\RecommendAgentProject 目录下
python -m rag.rag_engine
```

此命令将执行 `rag_engine.py` 中的测试用例，并打印输入和输出的JSON，展示模块的检索效果。

*注意: 为了让 `from rag...` 导入正常工作，您可能需要在 `rag` 文件夹中创建一个空的 `__init__.py` 文件。*

### 如何被 Agent 调用 (How to be Called by the Agent)

在 Phase 1 完成的 `RecommendationAgent` 可以轻松地与此 RAG 模块集成。

1.  **Agent 决策**: 首先，Agent 分析用户请求。如果其策略决策 `strategy.use_rag` 为 `true`，则意味着需要调用 RAG 模块。

2.  **调用 RAG 引擎**: Agent 或其后的流程控制器将实例化 `RagEngine`，并调用其 `search` 方法。

    ```python
    # 在 Agent 之后的某个流程控制器中
    from agent.recommendation_agent import RecommendationAgent
    from rag.rag_engine import RagEngine

    # 1. Agent 做出决策
    agent = RecommendationAgent()
    request_data = {"query": "寻找关于太空探索的电影", "context": {}}
    agent_decision = agent.decide(request_data)

    rag_candidates = []
    # 2. 如果 Agent 决定使用 RAG
    if agent_decision["strategy"]["use_rag"]:
        print("Agent decided to use RAG. Calling RAG Engine...")
        
        # 初始化 RAG 引擎
        rag_engine = RagEngine(data_path="data/datasets/movies.json")
        
        # 准备 RAG 输入
        rag_input = {
            "query": agent_decision["keywords"][0] or request_data["query"],
            "top_k": 10
        }
        
        # 获取 RAG 召回的候选集
        rag_result = rag_engine.search(rag_input)
        rag_candidates = rag_result["candidates"]
        
        print("RAG Candidates:", rag_candidates)

    # 3. 后续可以将 rag_candidates 与其他召回源（如 NCF、Rules）的候选集合并，
    # 然后送入排序模块。
    ```

通过这种方式，RAG 模块作为一个可插拔的语义召回组件，无缝地融入到整个推荐流程中。
