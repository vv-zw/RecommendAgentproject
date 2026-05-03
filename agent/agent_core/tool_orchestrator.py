# agent/agent_core/tool_orchestrator.py

import psycopg
import psycopg.rows
from movie_recommendation.config import Config


def _get_conn():
    url = Config.get_database_url()
    return psycopg.connect(url, row_factory=psycopg.rows.dict_row)


SCHEMA = Config.PGSCHEMA


def _content_item_to_result(row: dict) -> dict:
    """将 content_items 行转换为结构化推荐结果。"""
    genres_raw = row.get('genres') or ''
    if '/' in genres_raw:
        genres_list = [g.strip() for g in genres_raw.split('/') if g.strip()]
    else:
        genres_list = [genres_raw.strip()] if genres_raw.strip() else []
    return {
        'id': row.get('id'),
        'title': row.get('title', ''),
        'overview': row.get('plot', '') or '',
        'poster_path': row.get('cover_url', '') or '',
        'vote_average': float(row.get('rating', 0) or 0),
        'media_type': row.get('content_type', 'movie'),
        'genres': genres_list,
        'popularity': float(row.get('popularity', 0) or 0),
        'director': row.get('director', '') or '',
        'actors': row.get('actors', '') or '',
        'year': row.get('year'),
    }


class ToolOrchestrator:
    def execute_tools(
        self,
        user_id: str,
        intent: str,
        entities: dict,
        preference_context: dict | None = None
    ):
        """
        根据意图和实体执行对应工具，并结合用户偏好上下文优化结果。

        Args:
            user_id: 用户 ID
            intent: NLU 解析出的意图
            entities: NLU 解析出的实体
            preference_context: 用户偏好上下文 {'genres', 'directors', 'actors'}
        """
        if intent == "search_movie":
            return self._search_media(entities, preference_context)
        elif intent == "recommend_movie":
            return self._recommend_media('movie', entities, preference_context)
        elif intent == "recommend_series":
            return self._recommend_media('series', entities, preference_context)
        elif intent == "add_to_watchlist":
            return self._add_to_watchlist(user_id, entities)
        else:
            # 默认：基于偏好推荐电影
            return self._recommend_media('movie', entities, preference_context)

    def _build_preference_conditions(self, preference_context: dict | None) -> tuple:
        """根据偏好上下文构建 SQL 条件和参数。"""
        if not preference_context:
            return "", []

        match_conditions = []
        params = []

        for genre in (preference_context.get('genres') or [])[:3]:
            match_conditions.append("genres ILIKE %s")
            params.append(f"%{genre}%")
        for director in (preference_context.get('directors') or [])[:2]:
            match_conditions.append("director ILIKE %s")
            params.append(f"%{director}%")
        for actor in (preference_context.get('actors') or [])[:2]:
            match_conditions.append("actors ILIKE %s")
            params.append(f"%{actor}%")

        if match_conditions:
            return f"AND ({' OR '.join(match_conditions)})", params
        return "", []

    def _recommend_media(
        self,
        content_type: str,
        entities: dict,
        preference_context: dict | None = None,
        limit: int = 10
    ) -> list:
        """推荐影视内容，有偏好时优先匹配偏好，不足时补充热门内容。"""
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    results = []

                    # 1. 优先查询偏好匹配内容
                    if preference_context:
                        pref_cond, pref_params = self._build_preference_conditions(preference_context)
                        if pref_cond:
                            # 附加 genre 实体筛选
                            genre_filter = ""
                            genre_params: list = []
                            if entities.get('genre'):
                                genre_filter = " AND genres ILIKE %s"
                                genre_params.append(f"%{entities['genre']}%")

                            cur.execute(
                                f"""SELECT * FROM {SCHEMA}.content_items
                                    WHERE content_type = %s {pref_cond} {genre_filter}
                                    ORDER BY rating DESC, popularity DESC NULLS LAST
                                    LIMIT %s""",
                                [content_type] + pref_params + genre_params + [limit]
                            )
                            results = cur.fetchall()

                    # 2. 不足时补充热门内容
                    if len(results) < limit:
                        existing_ids = [r['id'] for r in results]
                        remaining = limit - len(results)

                        genre_filter = ""
                        genre_params_fallback: list = []
                        if entities.get('genre'):
                            genre_filter = " AND genres ILIKE %s"
                            genre_params_fallback.append(f"%{entities['genre']}%")

                        exclude_clause = ""
                        exclude_params: list = []
                        if existing_ids:
                            placeholders = ','.join(['%s'] * len(existing_ids))
                            exclude_clause = f" AND id NOT IN ({placeholders})"
                            exclude_params = existing_ids

                        cur.execute(
                            f"""SELECT * FROM {SCHEMA}.content_items
                                WHERE content_type = %s {genre_filter} {exclude_clause}
                                ORDER BY popularity DESC NULLS LAST
                                LIMIT %s""",
                            [content_type] + genre_params_fallback + exclude_params + [remaining]
                        )
                        results += cur.fetchall()

                    return [_content_item_to_result(r) for r in results]
        except Exception as e:
            print(f"ToolOrchestrator._recommend_media error: {e}")
            return []

    def _search_media(self, entities: dict, preference_context: dict | None = None) -> list:
        """搜索影视内容，有偏好时对结果进行偏好加权排序。"""
        query = entities.get('query', '')
        if not query:
            return self._recommend_media('movie', entities, preference_context)

        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""SELECT * FROM {SCHEMA}.content_items
                            WHERE title ILIKE %s
                            ORDER BY popularity DESC NULLS LAST
                            LIMIT 20""",
                        (f"%{query}%",)
                    )
                    rows = cur.fetchall()

            results = [_content_item_to_result(r) for r in rows]

            # 有偏好时对搜索结果进行偏好加权排序
            if preference_context and results:
                pref_genres = set(g.lower() for g in (preference_context.get('genres') or []))
                pref_directors = set(d.lower() for d in (preference_context.get('directors') or []))
                pref_actors = set(a.lower() for a in (preference_context.get('actors') or []))

                def preference_score(item: dict) -> float:
                    score = 0.0
                    item_genres = set(g.lower() for g in (item.get('genres') or []))
                    if item_genres & pref_genres:
                        score += 2.0
                    if item.get('director', '').lower() in pref_directors:
                        score += 1.5
                    actors_str = item.get('actors', '').lower()
                    if any(a in actors_str for a in pref_actors):
                        score += 1.0
                    return score

                results.sort(key=lambda x: (preference_score(x), x.get('popularity', 0)), reverse=True)

            return results
        except Exception as e:
            print(f"ToolOrchestrator._search_media error: {e}")
            return []

    def _add_to_watchlist(self, user_id: str, entities: dict) -> dict:
        """将影视内容添加到用户待看清单。"""
        media_id = entities.get('media_id')
        if not media_id:
            return {"status": "failure", "reason": "media_id not provided"}
        try:
            import uuid
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""INSERT INTO {SCHEMA}.watchlists (id, user_id, media_id)
                            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                        (str(uuid.uuid4()), user_id, media_id)
                    )
                conn.commit()
            return {"status": "success"}
        except Exception as e:
            print(f"ToolOrchestrator._add_to_watchlist error: {e}")
            return {"status": "failure", "reason": str(e)}
