"""
一次性建表脚本：创建 users、watchlists、watch_history、user_preferences 表
"""
import psycopg
from movie_recommendation.config import Config

url = Config.get_database_url()
schema = Config.PGSCHEMA

print(f"连接数据库，schema: {schema}")

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:

        # users 表
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}.users (
                id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ users 表已就绪")

        # watchlists 表
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}.watchlists (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                media_id BIGINT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, media_id)
            )
        """)
        print("✅ watchlists 表已就绪")

        # watch_history 表
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}.watch_history (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                media_id BIGINT NOT NULL,
                watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, media_id)
            )
        """)
        print("✅ watch_history 表已就绪")

        # user_preferences 表
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}.user_preferences (
                id BIGSERIAL PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                content_id VARCHAR(64) NOT NULL,
                content_type VARCHAR(16) NOT NULL CHECK (content_type IN ('movie', 'series')),
                title VARCHAR(255) NOT NULL,
                genres TEXT,
                rating NUMERIC(3,1) DEFAULT 0,
                year INTEGER,
                director VARCHAR(255),
                actors TEXT,
                cover_url TEXT,
                comment TEXT,
                source VARCHAR(64),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_user_preferences UNIQUE (user_id, content_id, content_type)
            )
        """)
        print("✅ user_preferences 表已就绪")

    conn.commit()

# 验证所有表
with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = %s ORDER BY table_name
        """, (schema,))
        tables = [r[0] for r in cur.fetchall()]

print(f"\n当前 {schema} schema 中的所有表：")
for t in tables:
    print(f"  - {t}")

print("\n✅ 所有表创建完成！现在可以注册账户了。")
