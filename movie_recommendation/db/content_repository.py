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
