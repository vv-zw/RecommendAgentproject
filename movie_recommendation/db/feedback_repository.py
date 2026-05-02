# movie_recommendation/db/feedback_repository.py

import uuid
from .connection import get_db_connection

class FeedbackRepository:
    # Watchlist Methods
    def get_watchlist(self, user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT mi.* FROM `medi-items` mi JOIN watchlists w ON mi.id = w.media_id WHERE w.user_id = %s ORDER BY w.added_at DESC",
                (user_id,)
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def add_to_watchlist(self, user_id, media_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        watchlist_id = str(uuid.uuid4())
        try:
            cursor.execute(
                "INSERT INTO watchlists (id, user_id, media_id) VALUES (%s, %s, %s)",
                (watchlist_id, user_id, media_id)
            )
            conn.commit()
            return True
        except Exception as e:
            print(e)
            return False
        finally:
            cursor.close()
            conn.close()

    def remove_from_watchlist(self, user_id, media_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM watchlists WHERE user_id = %s AND media_id = %s",
                (user_id, media_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    # Watch History Methods
    def get_watch_history(self, user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT mi.*, wh.watched_at FROM `medi-items` mi JOIN watch_history wh ON mi.id = wh.media_id WHERE wh.user_id = %s ORDER BY wh.watched_at DESC",
                (user_id,)
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def add_to_watch_history(self, user_id, media_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        history_id = str(uuid.uuid4())
        try:
            cursor.execute(
                "INSERT INTO watch_history (id, user_id, media_id, completed) VALUES (%s, %s, %s, 1) ON DUPLICATE KEY UPDATE watched_at=NOW(), completed=1",
                (history_id, user_id, media_id)
            )
            conn.commit()
            return True
        except Exception as e:
            print(e)
            return False
        finally:
            cursor.close()
            conn.close()
