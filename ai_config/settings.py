# ai_config/settings.py
import os

# --- Database Settings ---
# 从环境变量加载数据库URL，如果未设置则为空
DATABASE_URL = os.environ.get("DATABASE_URL")

# --- Feature Flags ---
# 控制是否开启Debug模式，输出详细的debug_trace
DEBUG_MODE_ENABLED = True

# 控制是否为每个推荐结果生成可解释性文本
EXPLAIN_ENABLED = True

# --- Logging Settings ---
LOG_FILE_PATH = "logs/app.log"
LOG_LEVEL = "INFO" # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# --- Fusion Weights ---
# 不同场景下的模型融合权重

# 默认权重 (适用于有行为历史的普通用户)
DEFAULT_FUSION_WEIGHTS = {
    "ncf": 0.4,
    "textcnn": 0.3,
    "rules": 0.3,
    "rag": 0.0 # RAG在本阶段默认不启用
}

# 冷启动用户权重 (无历史行为)
COLD_START_FUSION_WEIGHTS = {
    "ncf": 0.0, # NCF无法用于冷启动用户
    "textcnn": 0.5,
    "rules": 0.5,
    "rag": 0.0
}

# 纯类型查询权重 (例如“喜剧电影”)
GENRE_QUERY_FUSION_WEIGHTS = {
    "ncf": 0.1, # 大幅降低个性化权重，避免不相关类型污染
    "textcnn": 0.5, # 提升内容权重
    "rules": 0.4, # 提升规则权重
    "rag": 0.0
}

# 强语义查询权重 (例如包含“类似”等词语)
SEMANTIC_QUERY_FUSION_WEIGHTS = {
    "ncf": 0.3,
    "textcnn": 0.5, # 提升TextCNN的权重
    "rules": 0.2,
    "rag": 0.0
}
