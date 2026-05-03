import psycopg
from movie_recommendation.config import Config

url = Config.get_database_url()
print("连接URL:", url[:40], "...")

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
        schemas = [r[0] for r in cur.fetchall()]
        print("所有schema:", schemas)

        cur.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('pg_catalog','information_schema')
            ORDER BY table_schema, table_name
        """)
        tables = cur.fetchall()
        if tables:
            print("所有表:")
            for t in tables:
                print(f"  {t[0]}.{t[1]}")
        else:
            print("没有找到任何用户表！数据库是空的。")
