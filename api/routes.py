# api/routes.py
import datetime
import uuid
from flask import Blueprint, request, jsonify
import jwt
from functools import wraps

import psycopg
import psycopg.rows
from movie_recommendation.config import Config

# ── 数据库连接 ────────────────────────────────────────────────────
def get_conn():
    url = Config.get_database_url()
    return psycopg.connect(url, row_factory=psycopg.rows.dict_row)

SCHEMA = Config.PGSCHEMA  # 默认 "app"
SECRET_KEY = Config.SECRET_KEY

# ── JWT 认证装饰器 ────────────────────────────────────────────────
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT * FROM {SCHEMA}.users WHERE id = %s", (data['user_id'],)
                    )
                    current_user = cur.fetchone()
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# ── Blueprint ─────────────────────────────────────────────────────
api_bp = Blueprint('api', __name__)

# ── 工具函数 ──────────────────────────────────────────────────────
def serialize_row(row):
    """将数据库行中的特殊类型转为 JSON 可序列化格式"""
    if row is None:
        return None
    result = {}
    for k, v in row.items():
        if isinstance(v, (datetime.date, datetime.datetime)):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result

def content_item_to_media(row: dict) -> dict:
    """
    将 content_items 表的行转换为前端期望的 MediaItem 格式
    content_items 字段: id, source_item_id, content_type, title, original_title,
                        genres(text), rating, year, director, actors, cover_url,
                        plot, popularity, region, language, duration, episodes,
                        status, raw_source, created_at, updated_at
    """
    genres_raw = row.get('genres') or ''
    # genres 字段存储格式如 "科幻/动作/冒险" 或 "科幻 动作 冒险"
    if '/' in genres_raw:
        genres_list = [g.strip() for g in genres_raw.split('/') if g.strip()]
    elif ' ' in genres_raw:
        genres_list = [g.strip() for g in genres_raw.split() if g.strip()]
    else:
        genres_list = [genres_raw.strip()] if genres_raw.strip() else []

    return {
        'id': row.get('id'),
        'title': row.get('title', ''),
        'overview': row.get('plot', '') or '',
        'poster_path': row.get('cover_url', '') or '',
        'backdrop_path': row.get('cover_url', '') or '',
        'release_date': str(row.get('year', '')) if row.get('year') else '',
        'vote_average': float(row.get('rating', 0) or 0),
        'vote_count': 0,
        'media_type': row.get('content_type', 'movie'),
        'genres': genres_list,
        'popularity': float(row.get('popularity', 0) or 0),
        'director': row.get('director', '') or '',
        'actors': row.get('actors', '') or '',
        'region': row.get('region', '') or '',
        'language': row.get('language', '') or '',
        'duration': row.get('duration', '') or '',
    }

# ── 健康检查 ──────────────────────────────────────────────────────
@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()})

# ── 用户认证 ──────────────────────────────────────────────────────
@api_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    email    = (data.get('email') or '').strip()
    password = data.get('password') or ''

    if not all([username, email, password]):
        return jsonify({"error": "Missing username, email, or password"}), 400

    from werkzeug.security import generate_password_hash
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # 确保 users 表存在
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {SCHEMA}.users (
                        id VARCHAR(36) PRIMARY KEY,
                        username VARCHAR(100) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute(f"SELECT id FROM {SCHEMA}.users WHERE username = %s", (username,))
                if cur.fetchone():
                    return jsonify({"error": "Username already exists"}), 409
                user_id = str(uuid.uuid4())
                pw_hash = generate_password_hash(password)
                cur.execute(
                    f"INSERT INTO {SCHEMA}.users (id, username, email, password_hash) VALUES (%s, %s, %s, %s)",
                    (user_id, username, email, pw_hash)
                )
            conn.commit()
        return jsonify({"message": "User registered successfully", "user_id": user_id}), 201
    except Exception as e:
        print(f"Register error: {e}")
        return jsonify({"error": "Registration failed", "detail": str(e)}), 500


@api_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not all([username, password]):
        return jsonify({"error": "Missing username or password"}), 400

    from werkzeug.security import check_password_hash
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM {SCHEMA}.users WHERE username = %s", (username,))
                user = cur.fetchone()

        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid username or password"}), 401

        token = jwt.encode(
            {'user_id': user['id'],
             'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
            SECRET_KEY, algorithm="HS256"
        )
        return jsonify({"access_token": token, "token_type": "bearer", "user_id": user['id']})
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Login failed", "detail": str(e)}), 500

# ── 电影列表 ──────────────────────────────────────────────────────
@api_bp.route("/api/movies", methods=["GET"])
def get_movies():
    page    = request.args.get('page', 1, type=int)
    limit   = request.args.get('limit', 20, type=int)
    genre   = request.args.get('genre', type=str)
    year    = request.args.get('year', type=int)
    sort_by = request.args.get('sort_by', 'popularity.desc', type=str)
    offset  = (page - 1) * limit

    order_col = 'popularity'
    if 'rating' in sort_by or 'vote_average' in sort_by:
        order_col = 'rating'
    elif 'release_date' in sort_by or 'year' in sort_by:
        order_col = 'year'

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                where = ["content_type = 'movie'"]
                params: list = []

                if genre:
                    where.append("genres ILIKE %s")
                    params.append(f"%{genre}%")
                if year:
                    where.append("year = %s")
                    params.append(year)

                where_sql = " AND ".join(where)

                cur.execute(
                    f"SELECT COUNT(*) as cnt FROM {SCHEMA}.content_items WHERE {where_sql}",
                    params
                )
                total = cur.fetchone()['cnt']

                cur.execute(
                    f"""SELECT * FROM {SCHEMA}.content_items
                        WHERE {where_sql}
                        ORDER BY {order_col} DESC NULLS LAST
                        LIMIT %s OFFSET %s""",
                    params + [limit, offset]
                )
                rows = cur.fetchall()
                results = [content_item_to_media(r) for r in rows]

        return jsonify({"total": total, "page": page, "limit": limit, "results": results})
    except Exception as e:
        print(f"get_movies error: {e}")
        return jsonify({"error": "Failed to fetch movies", "detail": str(e)}), 500

# ── 剧集列表 ──────────────────────────────────────────────────────
@api_bp.route("/api/series", methods=["GET"])
def get_series():
    page    = request.args.get('page', 1, type=int)
    limit   = request.args.get('limit', 20, type=int)
    genre   = request.args.get('genre', type=str)
    year    = request.args.get('year', type=int)
    sort_by = request.args.get('sort_by', 'popularity.desc', type=str)
    offset  = (page - 1) * limit

    order_col = 'popularity'
    if 'rating' in sort_by or 'vote_average' in sort_by:
        order_col = 'rating'
    elif 'release_date' in sort_by or 'year' in sort_by:
        order_col = 'year'

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                where = ["content_type = 'series'"]
                params: list = []

                if genre:
                    where.append("genres ILIKE %s")
                    params.append(f"%{genre}%")
                if year:
                    where.append("year = %s")
                    params.append(year)

                where_sql = " AND ".join(where)

                cur.execute(
                    f"SELECT COUNT(*) as cnt FROM {SCHEMA}.content_items WHERE {where_sql}",
                    params
                )
                total = cur.fetchone()['cnt']

                cur.execute(
                    f"""SELECT * FROM {SCHEMA}.content_items
                        WHERE {where_sql}
                        ORDER BY {order_col} DESC NULLS LAST
                        LIMIT %s OFFSET %s""",
                    params + [limit, offset]
                )
                rows = cur.fetchall()
                results = [content_item_to_media(r) for r in rows]

        return jsonify({"total": total, "page": page, "limit": limit, "results": results})
    except Exception as e:
        print(f"get_series error: {e}")
        return jsonify({"error": "Failed to fetch series", "detail": str(e)}), 500

# ── 电影详情 ──────────────────────────────────────────────────────
@api_bp.route("/api/movies/<int:media_id>", methods=["GET"])
def get_movie_details(media_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT * FROM {SCHEMA}.content_items WHERE id = %s AND content_type = 'movie'",
                    (media_id,)
                )
                row = cur.fetchone()
        if not row:
            return jsonify({"error": "Movie not found"}), 404
        return jsonify(content_item_to_media(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── 剧集详情 ──────────────────────────────────────────────────────
@api_bp.route("/api/series/<int:media_id>", methods=["GET"])
def get_series_details(media_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT * FROM {SCHEMA}.content_items WHERE id = %s AND content_type = 'series'",
                    (media_id,)
                )
                row = cur.fetchone()
        if not row:
            return jsonify({"error": "Series not found"}), 404
        return jsonify(content_item_to_media(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── 搜索 ──────────────────────────────────────────────────────────
@api_bp.route("/api/search", methods=["GET"])
def search():
    query      = (request.args.get('query') or '').strip()
    media_type = request.args.get('media_type', type=str)
    page       = request.args.get('page', 1, type=int)
    limit      = request.args.get('limit', 20, type=int)
    offset     = (page - 1) * limit

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                where = ["title ILIKE %s"]
                params: list = [f"%{query}%"]
                if media_type:
                    where.append("content_type = %s")
                    params.append(media_type)
                where_sql = " AND ".join(where)

                cur.execute(
                    f"SELECT COUNT(*) as cnt FROM {SCHEMA}.content_items WHERE {where_sql}", params
                )
                total = cur.fetchone()['cnt']

                cur.execute(
                    f"""SELECT * FROM {SCHEMA}.content_items WHERE {where_sql}
                        ORDER BY popularity DESC NULLS LAST LIMIT %s OFFSET %s""",
                    params + [limit, offset]
                )
                results = [content_item_to_media(r) for r in cur.fetchall()]

        return jsonify({"total": total, "page": page, "limit": limit, "results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── 待看清单 ──────────────────────────────────────────────────────
def ensure_watchlist_table(cur):
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.watchlists (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            media_id BIGINT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, media_id)
        )
    """)

@api_bp.route("/api/users/<user_id>/watchlist", methods=["GET"])
@token_required
def get_watchlist(current_user, user_id):
    if str(current_user['id']) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                ensure_watchlist_table(cur)
                cur.execute(
                    f"""SELECT w.media_id, w.added_at, c.*
                        FROM {SCHEMA}.watchlists w
                        JOIN {SCHEMA}.content_items c ON w.media_id = c.id
                        WHERE w.user_id = %s ORDER BY w.added_at DESC""",
                    (user_id,)
                )
                rows = cur.fetchall()
                watchlist = []
                for r in rows:
                    item = content_item_to_media(r)
                    item['added_at'] = r['added_at'].isoformat() if r.get('added_at') else ''
                    watchlist.append(item)
        return jsonify({"watchlist": watchlist})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/users/<user_id>/watchlist", methods=["POST"])
@token_required
def add_to_watchlist(current_user, user_id):
    if str(current_user['id']) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403
    media_id = (request.get_json() or {}).get('media_id')
    if not media_id:
        return jsonify({"error": "media_id is required"}), 400
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                ensure_watchlist_table(cur)
                wid = str(uuid.uuid4())
                cur.execute(
                    f"INSERT INTO {SCHEMA}.watchlists (id, user_id, media_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (wid, user_id, media_id)
                )
            conn.commit()
        return jsonify({"message": "Item added to watchlist"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/users/<user_id>/watchlist/<media_id>", methods=["DELETE"])
@token_required
def remove_from_watchlist(current_user, user_id, media_id):
    if str(current_user['id']) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                ensure_watchlist_table(cur)
                cur.execute(
                    f"DELETE FROM {SCHEMA}.watchlists WHERE user_id = %s AND media_id = %s",
                    (user_id, media_id)
                )
            conn.commit()
        return jsonify({"message": "Item removed from watchlist"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── 观看历史 ──────────────────────────────────────────────────────
def ensure_history_table(cur):
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.watch_history (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            media_id BIGINT NOT NULL,
            watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, media_id)
        )
    """)

@api_bp.route("/api/users/<user_id>/history", methods=["GET"])
@token_required
def get_watch_history(current_user, user_id):
    if str(current_user['id']) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                ensure_history_table(cur)
                cur.execute(
                    f"""SELECT wh.watched_at, c.*
                        FROM {SCHEMA}.watch_history wh
                        JOIN {SCHEMA}.content_items c ON wh.media_id = c.id
                        WHERE wh.user_id = %s ORDER BY wh.watched_at DESC""",
                    (user_id,)
                )
                history = [content_item_to_media(r) for r in cur.fetchall()]
        return jsonify({"history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/users/<user_id>/history", methods=["POST"])
@token_required
def add_to_history(current_user, user_id):
    if str(current_user['id']) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403
    media_id = (request.get_json() or {}).get('media_id')
    if not media_id:
        return jsonify({"error": "media_id is required"}), 400
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                ensure_history_table(cur)
                hid = str(uuid.uuid4())
                cur.execute(
                    f"""INSERT INTO {SCHEMA}.watch_history (id, user_id, media_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, media_id) DO UPDATE SET watched_at = NOW()""",
                    (hid, user_id, media_id)
                )
            conn.commit()
        return jsonify({"message": "Watch history updated"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── 添加影视内容 ──────────────────────────────────────────────────
@api_bp.route("/api/content/add", methods=["POST"])
def add_content():
    data = request.get_json() or {}
    title      = (data.get('title') or '').strip()
    media_type = data.get('media_type', '')

    if not title or not media_type:
        return jsonify({"error": "title and media_type are required"}), 400
    if media_type not in ('movie', 'series'):
        return jsonify({"error": "media_type must be 'movie' or 'series'"}), 400

    try:
        genres_list = data.get('genres') or []
        genres_str  = '/'.join(genres_list) if genres_list else ''

        with get_conn() as conn:
            with conn.cursor() as cur:
                source_id = str(uuid.uuid4())
                cur.execute(
                    f"""INSERT INTO {SCHEMA}.content_items
                        (source_item_id, content_type, title, original_title,
                         genres, rating, year, plot, cover_url, popularity)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id""",
                    (
                        source_id,
                        media_type,
                        title,
                        data.get('original_title', ''),
                        genres_str,
                        float(data.get('vote_average', 0) or 0),
                        int(data.get('year', 0) or 0) or None,
                        data.get('overview', ''),
                        data.get('poster_path', ''),
                        float(data.get('popularity', 0) or 0),
                    )
                )
                new_id = cur.fetchone()['id']
            conn.commit()
        return jsonify({"message": "Content added successfully", "media_id": new_id}), 201
    except Exception as e:
        print(f"add_content error: {e}")
        return jsonify({"error": "Failed to add content", "detail": str(e)}), 500

# ── AI Agent ──────────────────────────────────────────────────────
@api_bp.route("/api/agent/chat", methods=["POST"])
@token_required
def chat(current_user):
    data    = request.get_json() or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    try:
        from agent.recommendation_agent import AgentManager
        agent = AgentManager()
        nl_response, structured_results = agent.process_user_request(
            current_user['id'], message
        )
        return jsonify({"nl_response": nl_response, "structured_results": structured_results})
    except Exception as e:
        print(f"Agent error: {e}")
        return jsonify({"error": "Agent execution failed", "detail": str(e)}), 500
