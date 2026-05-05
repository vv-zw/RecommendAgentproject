"""检查数据库中已爬取数据的情况"""
import sys
sys.path.insert(0, '.')
from movie_recommendation.config import Config
import psycopg

url = Config.get_database_url()
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row)
cur = conn.cursor()

# 总量和已填充字段统计
print("=== 各类型数据统计 ===")
cur.execute("""
    SELECT content_type,
           COUNT(*) as total,
           COUNT(director) as has_director,
           COUNT(plot) as has_plot,
           COUNT(year) as has_year
    FROM app.content_items
    GROUP BY content_type
""")
for r in cur.fetchall():
    print(r)

print()

# 区分豆瓣真实 ID（纯数字）和 UUID
print("=== source_item_id 类型分布 ===")
cur.execute("""
    SELECT content_type,
           COUNT(*) FILTER (WHERE source_item_id ~ '^[0-9]+$') as douban_id_count,
           COUNT(*) FILTER (WHERE source_item_id !~ '^[0-9]+$') as non_douban_count
    FROM app.content_items
    GROUP BY content_type
""")
for r in cur.fetchall():
    print(r)

print()
print("=== 非豆瓣ID的样本（前5条）===")
cur.execute("""
    SELECT source_item_id, content_type, title
    FROM app.content_items
    WHERE source_item_id !~ '^[0-9]+$'
    LIMIT 5
""")
for r in cur.fetchall():
    print(r)

print()
print("=== 豆瓣ID样本（前5条）===")
cur.execute("""
    SELECT source_item_id, content_type, title
    FROM app.content_items
    WHERE source_item_id ~ '^[0-9]+$'
    LIMIT 5
""")
for r in cur.fetchall():
    print(r)

conn.close()
