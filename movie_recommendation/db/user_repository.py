# movie_recommendation/db/user_repository.py

import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from .connection import get_db_connection

class UserRepository:
    def create_user(self, username, email, password):
        conn = get_db_connection()
        cursor = conn.cursor()
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(password)
        try:
            cursor.execute(
                "INSERT INTO users (id, username, email, password_hash) VALUES (%s, %s, %s, %s)",
                (user_id, username, email, password_hash)
            )
            conn.commit()
            return user_id
        finally:
            cursor.close()
            conn.close()

    def find_user_by_username(self, username):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def find_user_by_id(self, user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def check_password(self, user, password):
        return check_password_hash(user['password_hash'], password)
