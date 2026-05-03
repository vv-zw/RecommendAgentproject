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
    # autocommit=True 避免 context manager 自动 rollback
    conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row)
    conn.autocommit = True
    return conn

SCHEMA = Config.PGSCHEMA
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
                    cur.execute(f"SELECT * FROM {SCHEMA}.users WHERE id = %s", (data['user_id'],))
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
    genres_raw = row.get('genres') or ''
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


def build_preference_match_sql(preferences: list, content_type: str) -> tuple:
    """根据用户偏好构建 SQL WHERE 子句（OR 宽松匹配）。返回 (where_clause, params)"""
    conditions = [f"content_type = '{content_type}'"]
    params: list = []
    genre_set: set = set()
    director_set: set = set()
    actor_set: set = set()

    for pref in preferences:
        if pref.get('genres'):
            for g in pref['genres'].split('/'):
                g = g.strip()
                if g:
                    genre_set.add(g)
        if pref.get('director') and pref['director'].strip():
            director_set.add(pref['director'].strip())
        if pref.get('actors'):
            for a in pref['actors'].split('/'):
                a = a.strip()
                if a:
                    actor_set.add(a)

    match_conditions: list = []
    for g in genre_set:
        match_conditions.append("genres ILIKE %s")
        params.append(f"%{g}%")
    for d in director_set:
        match_conditions.append("director ILIKE %s")
        params.append(f"%{d}%")
    for a in actor_set:
        match_conditions.append("actors ILIKE %s")
        params.append(f"%{a}%")

    if match_conditions:
        conditions.append(f"({' OR '.join(match_conditions)})")

    return " AND ".join(conditions), params


def build_preference_context(preferences: list) -> dict:
    """将偏好记录聚合为 Agent 可用的上下文字典。"""
    genres: set = set()
    directors: set = set()
    actors: set = set()
    for pref in preferences:
        if pref.get('genres'):
            for g in pref['genres'].split('/'):
                if g.strip():
                    genres.add(g.strip())
        if pref.get('director') and pref['director'].strip():
            directors.add(pref['director'].strip())
        if pref.get('actors'):
            for a in pref['actors'].split('/'):
                if a.strip():
                    actors.add(a.strip())
    return {'genres': list(genres), 'directors': list(directors), 'actors': list(actors)}


def _query_preference_list(user_id: str, content_type: str,
                            page: int, limit: int,
                            genre: str | None, sort_by: str) -> dict:
    """偏好列表核心查询，供电影/剧集偏好接口复用。"""
    offset = (page - 1) * limit
    order_col = 'popularity'
    if 'rating' in sort_by or 'vote_average' in sort_by:
        order_col = 'rating'
    elif 'year' in sort_by or 'release_date' in sort_by:
        order_col = 'year'

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT genres, director, actors FROM {SCHEMA}.user_preferences "
                f"WHERE user_id = %s AND content_type = %s",
                (user_id, content_type)
            )
            preferences = cur.fetchall()
            is_fallback = len(preferences) == 0

            if is_fallback:
                where_sql = f"content_type = '{content_type}'"
                params: list = []
            else:
                where_sql, params = build_preference_match_sql(preferences, content_type)

            if genre:
                where_sql += " AND genres ILIKE %s"
                params.append(f"%{genre}%")

            cur.execute(
                f"SELECT COUNT(*) as cnt FROM {SCHEMA}.content_items WHERE {where_sql}", params
            )
            total = cur.fetchone()['cnt']

            cur.execute(
                f"""SELECT * FROM {SCHEMA}.content_items WHERE {where_sql}
                    ORDER BY {order_col} DESC NULLS LAST LIMIT %s OFFSET %s""",
                params + [limit, offset]
            )
            results = [content_item_to_media(r) for r in cur.fetchall()]

    return {"total": total, "page": page, "limit": limit, "is_fallback": is_fallback, "results": results}


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
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT id FROM {SCHEMA}.users WHERE username = %s", (username,))
                if cur.fetchone():
                    return jsonify({"error": "Username already exists"}), 409
                user_id = str(uuid.uuid4())
                cur.execute(
                    f"INSERT INTO {SCHEMA}.users (id, username, email, password_hash) VALUES (%s, %s, %s, %s)",
                    (user_id, username, email, generate_password_hash(password))
                )
            conn.commit()
        finally:
            conn.close()
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
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM {SCHEMA}.users WHERE username = %s", (username,))
                user = cur.fetchone()
        finally:
            conn.close()
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid username or password"}), 401
        token = jwt.encode(
            {'user_id': user['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
            SECRET_KEY, algorithm="HS256"
        )
        return jsonify({"access_token": token, "token_type": "bearer", "user_id": user['id']})
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Login failed", "detail": str(e)}), 500


# ── 全量电影/剧集列表（未登录或兜底用） ──────────────────────────
@api_bp.route("/api/movies", methods=["GET"])
def get_movies():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    genre = request.args.get('genre', type=str)
    year = request.args.get('year', type=int)
    sort_by = request.args.get('sort_by', 'popularity.desc', type=str)
    offset = (page - 1) * limit
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
                cur.execute(f"SELECT COUNT(*) as cnt FROM {SCHEMA}.content_items WHERE {where_sql}", params)
                total = cur.fetchone()['cnt']
                cur.execute(
                    f"SELECT * FROM {SCHEMA}.content_items WHERE {where_sql} ORDER BY {order_col} DESC NULLS LAST LIMIT %s OFFSET %s",
                    params + [limit, offset]
                )
                results = [content_item_to_media(r) for r in cur.fetchall()]
        return jsonify({"total": total, "page": page, "limit": limit, "results": results})
    except Exception as e:
        print(f"get_movies error: {e}")
        return jsonify({"error": "Failed to fetch movies", "detail": str(e)}), 500


@api_bp.route("/api/series", methods=["GET"])
def get_series():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    genre = request.args.get('genre', type=str)
    year = request.args.get('year', type=int)
    sort_by = request.args.get('sort_by', 'popularity.desc', type=str)
    offset = (page - 1) * limit
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
                cur.execute(f"SELECT COUNT(*) as cnt FROM {SCHEMA}.content_items WHERE {where_sql}", params)
                total = cur.fetchone()['cnt']
                cur.execute(
                    f"SELECT * FROM {SCHEMA}.content_items WHERE {where_sql} ORDER BY {order_col} DESC NULLS LAST LIMIT %s OFFSET %s",
                    params + [limit, offset]
                )
                results = [content_item_to_media(r) for r in cur.fetchall()]
        return jsonify({"total": total, "page": page, "limit": limit, "results": results})
    except Exception as e:
        print(f"get_series error: {e}")
        return jsonify({"error": "Failed to fetch series", "detail": str(e)}), 500


# ── 详情 ──────────────────────────────────────────────────────────
@api_bp.route("/api/movies/<int:media_id>", methods=["GET"])
def get_movie_details(media_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM {SCHEMA}.content_items WHERE id = %s AND content_type = 'movie'", (media_id,))
                row = cur.fetchone()
        if not row:
            return jsonify({"error": "Movie not found"}), 404
        return jsonify(content_item_to_media(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/series/<int:media_id>", methods=["GET"])
def get_series_details(media_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM {SCHEMA}.content_items WHERE id = %s AND content_type = 'series'", (media_id,))
                row = cur.fetchone()
        if not row:
            return jsonify({"error": "Series not found"}), 404
        return jsonify(content_item_to_media(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 搜索 ──────────────────────────────────────────────────────────
@api_bp.route("/api/search", methods=["GET"])
def search():
    query = (request.args.get('query') or '').strip()
    media_type = request.args.get('media_type', type=str)
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
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
                cur.execute(f"SELECT COUNT(*) as cnt FROM {SCHEMA}.content_items WHERE {where_sql}", params)
                total = cur.fetchone()['cnt']
                cur.execute(
                    f"SELECT * FROM {SCHEMA}.content_items WHERE {where_sql} ORDER BY popularity DESC NULLS LAST LIMIT %s OFFSET %s",
                    params + [limit, offset]
                )
                results = [content_item_to_media(r) for r in cur.fetchall()]
        return jsonify({"total": total, "page": page, "limit": limit, "results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 待看清单 ──────────────────────────────────────────────────────
def ensure_watchlist_table(cur):
    cur.execute(f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.watchlists (
        id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL,
        media_id BIGINT NOT NULL, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, media_id))""")


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
                cur.execute(
                    f"INSERT INTO {SCHEMA}.watchlists (id, user_id, media_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (str(uuid.uuid4()), user_id, media_id)
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
    cur.execute(f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.watch_history (
        id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL,
        media_id BIGINT NOT NULL, watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, media_id))""")


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
                    f"""SELECT wh.watched_at, c.* FROM {SCHEMA}.watch_history wh
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
                cur.execute(
                    f"""INSERT INTO {SCHEMA}.watch_history (id, user_id, media_id) VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, media_id) DO UPDATE SET watched_at = NOW()""",
                    (str(uuid.uuid4()), user_id, media_id)
                )
            conn.commit()
        return jsonify({"message": "Watch history updated"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 添加影视内容 ──────────────────────────────────────────────────
@api_bp.route("/api/content/add", methods=["POST"])
def add_content():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    media_type = data.get('media_type', '')
    if not title or not media_type:
        return jsonify({"error": "title and media_type are required"}), 400
    if media_type not in ('movie', 'series'):
        return jsonify({"error": "media_type must be 'movie' or 'series'"}), 400
    try:
        genres_str = '/'.join(data.get('genres') or [])
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""INSERT INTO {SCHEMA}.content_items
                        (source_item_id, content_type, title, original_title, genres, rating, year, plot, cover_url, popularity)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (str(uuid.uuid4()), media_type, title, data.get('original_title', ''), genres_str,
                     float(data.get('vote_average', 0) or 0), int(data.get('year', 0) or 0) or None,
                     data.get('overview', ''), data.get('poster_path', ''), float(data.get('popularity', 0) or 0))
                )
                new_id = cur.fetchone()['id']
            conn.commit()
        return jsonify({"message": "Content added successfully", "media_id": new_id}), 201
    except Exception as e:
        print(f"add_content error: {e}")
        return jsonify({"error": "Failed to add content", "detail": str(e)}), 500


# ── 偏好电影接口（已登录用户专用） ───────────────────────────────
@api_bp.route("/api/users/<user_id>/movies/preference", methods=["GET"])
@token_required
def get_preference_movies(current_user, user_id):
    """返回基于用户偏好筛选的电影列表；无偏好时兜底全量并标记 is_fallback=true。"""
    if str(current_user['id']) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403
    page    = request.args.get('page', 1, type=int)
    limit   = request.args.get('limit', 20, type=int)
    genre   = request.args.get('genre', type=str)
    sort_by = request.args.get('sort_by', 'popularity.desc', type=str)
    try:
        result = _query_preference_list(user_id, 'movie', page, limit, genre, sort_by)
        return jsonify(result)
    except Exception as e:
        print(f"get_preference_movies error: {e}")
        return jsonify({"error": "Failed to fetch preference movies", "detail": str(e)}), 500


# ── 偏好剧集接口（已登录用户专用） ───────────────────────────────
@api_bp.route("/api/users/<user_id>/series/preference", methods=["GET"])
@token_required
def get_preference_series(current_user, user_id):
    """返回基于用户偏好筛选的剧集列表；无偏好时兜底全量并标记 is_fallback=true。"""
    if str(current_user['id']) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403
    page    = request.args.get('page', 1, type=int)
    limit   = request.args.get('limit', 20, type=int)
    genre   = request.args.get('genre', type=str)
    sort_by = request.args.get('sort_by', 'popularity.desc', type=str)
    try:
        result = _query_preference_list(user_id, 'series', page, limit, genre, sort_by)
        return jsonify(result)
    except Exception as e:
        print(f"get_preference_series error: {e}")
        return jsonify({"error": "Failed to fetch preference series", "detail": str(e)}), 500


# ── 用户偏好查询接口 ──────────────────────────────────────────────
@api_bp.route("/api/users/<user_id>/preferences", methods=["GET"])
@token_required
def get_user_preferences(current_user, user_id):
    """返回用户所有偏好记录，供前端生成快捷词条和 Agent 上下文使用。"""
    if str(current_user['id']) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT * FROM {SCHEMA}.user_preferences WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
                preferences = [serialize_row(r) for r in cur.fetchall()]
        return jsonify({"preferences": preferences})
    except Exception as e:
        print(f"get_user_preferences error: {e}")
        return jsonify({"error": "Failed to fetch user preferences", "detail": str(e)}), 500


# ── AI Agent（注入偏好上下文） ────────────────────────────────────
@api_bp.route("/api/agent/chat", methods=["POST"])
@token_required
def chat(current_user):
    data    = request.get_json() or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    # 偏好上下文查询失败时静默降级，不影响对话功能
    preference_context = None
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT genres, director, actors FROM {SCHEMA}.user_preferences WHERE user_id = %s",
                    (current_user['id'],)
                )
                preferences = cur.fetchall()
        if preferences:
            preference_context = build_preference_context(preferences)
    except Exception as e:
        print(f"Failed to load preference context: {e}")

    try:
        from agent.recommendation_agent import AgentManager
        agent = AgentManager()
        nl_response, structured_results = agent.process_user_request(
            current_user['id'], message, preference_context
        )
        return jsonify({"nl_response": nl_response, "structured_results": structured_results})
    except Exception as e:
        print(f"Agent error: {e}")
        return jsonify({"error": "Agent execution failed", "detail": str(e)}), 500
