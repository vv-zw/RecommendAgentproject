# movie_recommendation/db/content_repository.py

from .connection import get_db_connection

class ContentRepository:
    def get_media_list(self, media_type, page=1, limit=20, genre=None, year=None, sort_by='popularity.desc'):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        offset = (page - 1) * limit

        query = f"""SELECT * FROM `media_items` WHERE media_type = %s """
        params = [media_type]

        if genre:
            query += "AND id IN (SELECT media_id FROM `media_genres` mg JOIN genres g ON mg.genre_id = g.id WHERE g.name = %s) "
            params.append(genre)
        
        if year:
            query += "AND YEAR(release_date) = %s "
            params.append(year)

        if sort_by == 'popularity.desc':
            query += "ORDER BY popularity DESC "
        elif sort_by == 'vote_average.desc':
            query += "ORDER BY vote_average DESC "

        query += "LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        try:
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Get total count for pagination
            count_query = query.replace("SELECT *", "SELECT COUNT(*)").split("LIMIT")[0]
            cursor.execute(count_query, params[:-2]) # Exclude limit and offset
            total = cursor.fetchone()['COUNT(*)']

            return results, total
        finally:
            cursor.close()
            conn.close()

    def get_media_by_id(self, media_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM `media_items` WHERE id = %s", (media_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def search_media(self, query, media_type=None, page=1, limit=20):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        offset = (page - 1) * limit

        sql_query = "SELECT * FROM `media_items` WHERE title LIKE %s "
        params = [f"%{query}%"]

        if media_type:
            sql_query += "AND media_type = %s "
            params.append(media_type)

        sql_query += "LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        try:
            cursor.execute(sql_query, params)
            results = cursor.fetchall()

            count_query = sql_query.replace("SELECT *", "SELECT COUNT(*)").split("LIMIT")[0]
            cursor.execute(count_query, params[:-2])
            total = cursor.fetchone()['COUNT(*)']

            return results, total
        finally:
            cursor.close()
            conn.close()

    def add_media_item(self, title, media_type, overview='', release_date=None,
                       vote_average=0.0, vote_count=0, popularity=0.0,
                       poster_path='', backdrop_path='', genres=None):
        """手动添加一条影视记录，返回新记录的 id"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """INSERT INTO `media_items`
                   (title, media_type, overview, release_date,
                    vote_average, vote_count, popularity,
                    poster_path, backdrop_path)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (title, media_type, overview, release_date or None,
                 vote_average, vote_count, popularity,
                 poster_path, backdrop_path)
            )
            media_id = cursor.lastrowid

            # 处理 genres（字符串列表）
            if genres:
                for genre_name in genres:
                    genre_name = genre_name.strip()
                    if not genre_name:
                        continue
                    # 查找或创建 genre
                    cursor.execute(
                        "SELECT id FROM `genres` WHERE name = %s", (genre_name,)
                    )
                    row = cursor.fetchone()
                    if row:
                        genre_id = row['id']
                    else:
                        cursor.execute(
                            "INSERT INTO `genres` (name) VALUES (%s)", (genre_name,)
                        )
                        genre_id = cursor.lastrowid
                    # 关联
                    cursor.execute(
                        "INSERT IGNORE INTO `media_genres` (media_id, genre_id) VALUES (%s, %s)",
                        (media_id, genre_id)
                    )

            conn.commit()
            return media_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
