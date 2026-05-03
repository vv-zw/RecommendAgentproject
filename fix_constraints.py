"""
修复 user_preferences 表缺失的唯一约束
"""
import psycopg
from movie_recommendation.config import Config

url = Config.get_database_url()
schema = Config.PGSCHEMA

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        # 检查约束是否已存在
        cur.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_schema = %s
              AND table_name = 'user_preferences'
              AND constraint_type = 'UNIQUE'
        """, (schema,))
        existing = [r[0] for r in cur.fetchall()]
        print("现有唯一约束:", existing)

        if 'uq_user_preferences' not in existing:
            # 先清理可能存在的重复数据
            cur.execute(f"""
                DELETE FROM {schema}.user_preferences
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM {schema}.user_preferences
                    GROUP BY user_id, content_id, content_type
                )
            """)
            deleted = cur.rowcount
            print(f"清理重复数据: {deleted} 条")

            # 添加唯一约束
            cur.execute(f"""
                ALTER TABLE {schema}.user_preferences
                ADD CONSTRAINT uq_user_preferences
                UNIQUE (user_id, content_id, content_type)
            """)
            print("✅ 唯一约束 uq_user_preferences 已添加")
        else:
            print("✅ 唯一约束已存在，无需修复")

    conn.commit()
    print("完成！现在可以正常添加影片了。")
