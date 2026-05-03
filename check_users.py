import psycopg
from movie_recommendation.config import Config

url = Config.get_database_url()
schema = Config.PGSCHEMA

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT id, username, email, created_at FROM {schema}.users ORDER BY created_at DESC")
        users = cur.fetchall()

if users:
    print(f"数据库中共 {len(users)} 个用户：")
    for u in users:
        print(f"  id={u[0][:8]}... username={u[1]} email={u[2]} created={u[3]}")
else:
    print("数据库中没有任何用户，请先注册")
