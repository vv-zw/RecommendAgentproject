-- ==========================================
-- 数据库初始化脚本
-- 在 PostgreSQL 容器首次启动时自动执行
-- ==========================================

-- 启用 pgvector 扩展（向量检索用）
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建应用 schema
CREATE SCHEMA IF NOT EXISTS app;

-- 授权给 postgres 用户
GRANT ALL ON SCHEMA app TO postgres;

-- 设置默认 schema
ALTER USER postgres SET search_path TO app, public;

-- 打印成功信息
SELECT 'Database initialized successfully with pgvector extension' AS status;
