# AI 电影推荐系统 - 整体架构说明

本文档是整个 AI 电影推荐系统的最终架构和使用说明。项目采用前后端分离的设计，并通过一个统一的 AI 编排层将推荐算法、决策智能与用户界面连接起来。

## 1. 系统启动指南

要运行整个系统，只需从项目根目录执行 `app.py` 文件：

```bash
# 确保您在 d:\RecommendAgentProject 目录下
python movie_recommendation/app.py
```

启动成功后，您会看到类似以下的输出：
`* Running on http://127.0.0.1:5000`

现在，打开您的浏览器并访问 **`http://127.0.0.1:5000`**，即可看到 AI 推荐系统的用户界面。

## 2. 技术架构

系统分为三个核心层次：前端展示层、后端API层、AI能力层。

### 2.1 前端展示层 (`frontend/`)
- **技术栈**: 原生 HTML, CSS, JavaScript (Vanilla JS)。
- **职责**: 
  - 提供用户交互界面（聊天输入框）。
  - 调用后端 AI 推荐接口。
  - 以卡片形式展示推荐的电影列表。
  - **可视化 AI 思考过程**：将后端的决策和调试信息，以人类可读的方式呈现给用户。
  - 提供调试面板，展示完整的后端返回JSON。

### 2.2 后端 API 层 (`movie_recommendation/app.py`)
- **技术栈**: Flask
- **核心接口**:
  - `GET /`: 托管并返回前端 `index.html` 页面。
  - `POST /api/ai/recommend/full`: **系统统一入口**。该接口负责接收前端请求，并完成整个 AI 推荐的端到端调用。
- **职责**: 作为前端和 AI 能力层之间的桥梁，处理 HTTP 请求，并调用内部 AI 模块。

### 2.3 AI 能力层

这是系统的“大脑”，由多个解耦的模块构成：

1.  **Phase 1: Recommendation Agent (`agent/`)**
    - **输入**: 用户查询 (`query`)。
    - **职责**: 理解用户意图，提取特征，并制定一个推荐**策略**（例如，决定是否使用 NCF、TextCNN 等）。
    - **输出**: 一个结构化的**决策 JSON**。

2.  **Phase 2: RAG Semantic Retrieval (`rag/`)** (按需调用)
    - **输入**: 查询文本。
    - **职责**: 基于 TF-IDF 和余弦相似度，从电影库中召回语义相关的候选集。
    - **输出**: 候选电影列表。

3.  **Phase 3: Recommendation Orchestrator (`orchestrator/`)**
    - **输入**: Agent 的决策 JSON。
    - **职责**: 
        - 根据 Agent 的策略，**调用**一个或多个现有的推荐模型（`recommendation/` 目录下的模拟模型）。
        - 对多路召回的结果进行**动态加权融合**。
        - 对结果进行**过滤**（如去重、移除已看）。
    - **输出**: 最终的、排好序的推荐列表及调试信息。

4.  **Phase 4: Explanation Generator (`orchestrator/explanation_generator.py`)**
    - **输入**: Agent 的决策和 Orchestrator 的输出。
    - **职责**: 将机器可读的调试信息，翻译成用户友好的、分步骤的**推荐理由**。
    - **输出**: 一段可供前端展示的解释文本。

## 3. 端到端数据流

当用户在前端点击“发送”按钮后，系统内部会发生以下一系列事件：

1.  **[前端]** `script.js` 向后端 `POST /api/ai/recommend/full` 发送包含 `query` 的请求。
2.  **[后端 `app.py`]** `full_ai_recommend` 函数被触发。
3.  **[调用 Agent]** `app.py` 实例化并调用 `RecommendationAgent`，获得**决策**。
4.  **[调用 Orchestrator]** `app.py` 将 Agent 的决策传递给 `RecommendationOrchestrator`。
5.  **[Orchestrator 内部]**
    a. 根据决策调用 `recommendation/` 下的 `ncf`, `textcnn`, `rule_based` 等函数。
    b. `fusion.py` 对返回的多路结果进行加权融合。
    c. `filter.py` 清洗融合后的列表。
6.  **[调用 Explanation]** `app.py` 调用 `generate_explanation`，生成推荐理由。
7.  **[返回前端]** `app.py` 将最终的推荐列表、解释文本和详细的调试信息组装成一个 JSON，返回给前端。
8.  **[前端渲染]** `script.js` 接收到 JSON 数据，并动态地将电影卡片、解释文本和调试信息渲染到页面上。

通过这种分层、解耦的架构，我们实现了一个灵活、可扩展且可解释的 AI 推荐系统。
