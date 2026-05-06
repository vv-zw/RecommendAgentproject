"""安装 pgvector 扩展并添加 embedding 列"""
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv('.env', override=True)
from movie_recommendation.config import Config
import psycopg

conn = psycopg.connect(Config.get_database_url())
conn.autocommit = True
cur = conn.cursor()

# 1. 安装 pgvector
print("安装 pgvector 扩展...")
cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
print("pgvector 安装成功")

# 2. 添加 embedding 列（1536 维，兼容 OpenAI text-embedding-3-small 和 DeepSeek）
print("添加 embedding 列...")
cur.execute("""
    ALTER TABLE app.content_items
    ADD COLUMN IF NOT EXISTS embedding vector(1536)
""")
print("embedding 列添加成功")

# 3. 创建向量索引（IVFFlat，适合 1000+ 条数据）
print("创建向量索引...")
cur.execute("""
    CREATE INDEX IF NOT EXISTS content_items_embedding_idx
    ON app.content_items
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50)
""")
print("向量索引创建成功")

conn.close()
print("\n全部完成！")
