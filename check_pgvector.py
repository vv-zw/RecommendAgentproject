import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv('.env', override=True)
from movie_recommendation.config import Config
import psycopg

conn = psycopg.connect(Config.get_database_url())
cur = conn.cursor()

# 检查 pgvector 是否已安装
cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
row = cur.fetchone()
print("pgvector 已安装" if row else "pgvector 未安装，需要执行 CREATE EXTENSION vector")

# 检查 content_items 是否有 embedding 列
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_schema = 'app' AND table_name = 'content_items' AND column_name = 'embedding'
""")
col = cur.fetchone()
print("embedding 列已存在" if col else "embedding 列不存在，需要 ALTER TABLE")

conn.close()
