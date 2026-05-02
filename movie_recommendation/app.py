import json
import os
import traceback
import random
import sys
import threading
import uuid
from datetime import datetime
from flask import Flask, jsonify, request, make_response, send_file
import pandas as pd

PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
if PACKAGE_ROOT not in sys.path:
    sys.path.insert(0, PACKAGE_ROOT)

# Force UTF-8 console output on Windows to avoid emoji log crashes under GBK code page.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# imghdr 在 Python 3.13+ 中已移除，使用替代方案
def detect_image_type(image_data):
    """检测图片类型（替代 imghdr）"""
    if image_data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    elif image_data[:3] == b'\xff\xd8\xff':
        return 'jpeg'
    elif image_data[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
        return 'webp'
    elif image_data[:2] == b'BM':
        return 'bmp'
    else:
        return 'jpeg'  # 默认

# Flask应用初始化
from flask_cors import CORS

# 配置导入容错
try:
    from config import Config

    config_instance = Config()
    print("[OK] 成功加载配置文件")
except (ImportError, ModuleNotFoundError) as e:
    print(f"[WARN] 配置文件导入失败: {e}")


    # 创建默认配置
    class DefaultConfig:
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DATASET_PATHS = {
            'movie': os.path.join(BASE_DIR, 'data', 'douban_movies.csv'),
            'series': os.path.join(BASE_DIR, 'data', 'douban_series.csv')
        }
        RECOMMEND_OUTPUT_PATH = {
            'movie': os.path.join(BASE_DIR, 'data', 'movie_recommendations.json'),
            'series': os.path.join(BASE_DIR, 'data', 'series_recommendations.json')
        }
        USER_DATA_FILE = os.path.join(BASE_DIR, 'data', 'user_data.json')
        WATCHLIST_FILE = os.path.join(BASE_DIR, 'data', 'watchlist.json')


    config_instance = DefaultConfig()

# 其他模块导入（添加容错）
try:
    from utils.file_utils import safe_read_json, safe_write_json
    from utils.image_utils import proxy_image, is_allowed_domain
    from utils.text_utils import calculate_similarity
    from recommendation.engine import (
        add_negative_feedback,
        build_recommendation_reason_summary,
        calculate_preference_weights,
        generate_and_save_recommendations,
        generate_personalized_recommendations,
        get_current_recommendation_signature,
        get_behavior_for_type,
        get_count_weights_for_type,
        get_preferences_for_type,
        init_or_repair_user_data,
        normalize_recommendation_item,
        normalize_preferences_payload,
        rotate_cached_recommendations,
        sort_weight_map,
        safe_read_csv,
    )
    from db.user_repository import clear_user_preferences, get_user_preferences, replace_user_preferences
    from search.search_engine import (
        batch_search_dramas,
        batch_search_items_by_names,
        search_drama_by_name,
        search_item_by_name as search_item_by_name_service,
        smart_search,
    )
    from watchlist.manager import manage_watchlist

    # --- AI Recommendation Pipeline Imports ---
    # Phase 1: Agent
    from agent.recommendation_agent import RecommendationAgent
    # Phase 3: Orchestrator & Components
    from orchestrator.recommendation_orchestrator import RecommendationOrchestrator
    from orchestrator.fusion import get_fusion_weights # Import specific function
    # Phase 5: Engineering & Explainability Layer
    from config import settings
    from logging.logger import logger # Use the pre-configured logger instance
    from explain.explanation_generator import generate_per_item_explanations
    from debug.debug_builder import build_debug_trace

    print("[OK] 成功加载所有模块")
except ImportError as e:
    # Use logger if available, otherwise print
    try:
        from logging.logger import logger
        logger.error(f"[FATAL] 模块导入失败: {e}")
    except ImportError:
        print(f"[FATAL] 模块导入失败: {e}")


    # 创建占位函数避免崩溃
    def safe_read_json(path, default=None):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default or {}


    def safe_write_json(path, data):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

app = Flask(__name__)
app.secret_key = getattr(config_instance, "SECRET_KEY", "dev-secret-key-change-in-production")
CORS(app, resources={r"/*": {"origins": "*"}})  # 更宽松的CORS配置

# AI Pipeline Singleton Instances
agent = RecommendationAgent()
orchestrator = RecommendationOrchestrator()

# 全局配置引用
Config = config_instance
refresh_jobs = {}
refresh_jobs_lock = threading.Lock()

try:
    from admin import admin_api_bp, admin_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_api_bp)
except ImportError as e:
    print(f"[WARN] 管理后台模块导入失败: {e}")


def build_refresh_job(recommend_type):
    """Create an in-memory refresh job and return its id."""
    job_id = f"{recommend_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    with refresh_jobs_lock:
        refresh_jobs[job_id] = {
            "job_id": job_id,
            "type": recommend_type,
            "status": "queued",
            "error": "",
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "started_at": "",
            "finished_at": "",
        }
    return job_id


def build_completed_refresh_job(recommend_type, reused=False):
    """Create an already-finished refresh job for cache hits."""
    job_id = f"{recommend_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with refresh_jobs_lock:
        refresh_jobs[job_id] = {
            "job_id": job_id,
            "type": recommend_type,
            "status": "done",
            "error": "",
            "created_at": now,
            "started_at": now,
            "finished_at": now,
            "reused": reused,
        }
    return job_id


def run_refresh_job(job_id, recommend_type):
    """Execute recommendation refresh in a background thread."""
    with refresh_jobs_lock:
        job = refresh_jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["started_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        refresh_result = generate_and_save_recommendations(recommend_type, force_refresh=True)
        ok = bool(refresh_result.get('ok')) if isinstance(refresh_result, dict) else bool(refresh_result)
        with refresh_jobs_lock:
            job = refresh_jobs.get(job_id)
            if not job:
                return
            job["status"] = "done" if ok else "failed"
            if not ok:
                job["error"] = refresh_result.get('error', 'refresh_failed') if isinstance(refresh_result, dict) else "refresh_failed"
            else:
                job["reused"] = bool(refresh_result.get('reused')) if isinstance(refresh_result, dict) else False
            job["finished_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    except Exception as exc:
        with refresh_jobs_lock:
            job = refresh_jobs.get(job_id)
            if not job:
                return
            job["status"] = "failed"
            job["error"] = str(exc)
            job["finished_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def start_refresh_job(recommend_type):
    """Start a refresh thread for one content type."""
    job_id = build_refresh_job(recommend_type)
    thread = threading.Thread(target=run_refresh_job, args=(job_id, recommend_type), daemon=True)
    thread.start()
    return job_id


# --------------------------
# 工具函数（避免重复代码）
# --------------------------
def search_item_by_name(item_name, item_type='movie'):
    """通用的项目搜索函数"""
    try:
        db_result = search_item_by_name_service(item_name, item_type)
        if db_result:
            return db_result, None

        # 获取数据集路径
        csv_path = Config.DATASET_PATHS.get(item_type)
        if not os.path.exists(csv_path):
            return None, "数据集不存在"

        # 读取CSV
        df = safe_read_csv(csv_path)
        if df.empty:
            return None, "数据集为空"

        best_match = None
        best_score = 0

        for _, row in df.iterrows():
            title = str(row.get('title', '')).strip()
            if not title:
                continue

            # 计算相似度
            similarity = calculate_similarity(item_name, title)

            # 完全匹配优先
            if item_name.lower() == title.lower():
                best_match = row
                best_score = 1.0
                break

            # 相似度超过阈值
            if similarity > 0.7 and similarity > best_score:
                best_match = row
                best_score = similarity

        if best_match is None:
            return None, "未找到匹配项"

        # 构建结果
        result = {
            "id": str(best_match.get('id', '')),
            "title": str(best_match.get('title', '')),
            "name": str(best_match.get('name', str(best_match.get('title', '')))),
            "genres": str(best_match.get('genres', '')),
            "rating": str(best_match.get('rating', '')),
            "cover_url": str(best_match.get('cover_url', '')),
            "coverUrl": str(best_match.get('cover_url', '')),
            "year": str(best_match.get('year', '')),
            "director": str(best_match.get('director', '')),
            "actors": str(best_match.get('actors', '')),
            "popularity": str(best_match.get('popularity', '')),
            "similarity_score": best_score
        }

        # 添加类型特有字段
        if item_type == 'movie':
            result.update({
                "duration": str(best_match.get('duration', best_match.get('runtime', '未知时长'))),
                "country": str(best_match.get('country', best_match.get('region', '未知国家'))),
                "language": str(best_match.get('language', '未知语言')),
                "release_date": str(best_match.get('release_date', best_match.get('release_time', ''))),
                "box_office": str(best_match.get('box_office', '未知票房'))
            })
        else:  # series
            result.update({
                "episodes": str(best_match.get('episodes', best_match.get('total_episodes', '未知集数'))),
                "region": str(best_match.get('region', best_match.get('area', '未知地区'))),
                "status": str(best_match.get('status', '完结'))
            })

        return result, None

    except Exception as e:
        return None, str(e)


# --------------------------
# API接口实现
# --------------------------
@app.route("/api/movies", methods=["GET"])
def get_movies_data():
    """获取电影CSV数据（JSON格式）"""
    try:
        # 读取CSV文件
        movie_df = safe_read_csv(Config.DATASET_PATHS['movie'])
        if movie_df.empty:
            return jsonify({
                "code": 404,
                "error": "电影数据文件不存在或为空"
            }), 404

        # 转换为JSON格式
        movies_data = movie_df.to_dict('records')

        return jsonify({
            "code": 0,
            "data": movies_data,
            "count": len(movies_data)
        })

    except Exception as e:
        print(f"获取电影数据失败: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 500,
            "error": f"服务器错误: {str(e)}"
        }), 500


@app.route("/api/download-csv", methods=["GET"]) #从后端服务器本地读取已存储的影视数据 CSV 文件
def download_csv():
    """直接下载CSV文件"""
    try:
        csv_type = request.args.get('type', 'movie')
        csv_path = Config.DATASET_PATHS.get(csv_type, Config.DATASET_PATHS['movie'])

        if not os.path.exists(csv_path):
            return jsonify({
                "code": 404,
                "error": f"{csv_type} CSV文件不存在"
            }), 404

        # 返回CSV文件
        return send_file(
            csv_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'douban_{csv_type}s.csv'
        )

    except Exception as e:
        print(f"下载CSV失败: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 500,
            "error": f"服务器错误: {str(e)}"
        }), 500


@app.route("/api/csv-text", methods=["GET"]) #通过接口返回给前端
def get_csv_text():
    """获取CSV原始文本内容"""
    try:
        csv_type = request.args.get('type', 'movie')
        csv_path = Config.DATASET_PATHS.get(csv_type, Config.DATASET_PATHS['movie'])

        if not os.path.exists(csv_path):
            return jsonify({
                "code": 404,
                "error": f"{csv_type} CSV文件不存在"
            }), 404

        # 读取CSV文件内容
        encodings = ['utf-8', 'gbk', 'latin-1', 'gb2312']
        csv_content = None

        for encoding in encodings:
            try:
                with open(csv_path, 'r', encoding=encoding) as f:
                    csv_content = f.read()
                break
            except (UnicodeDecodeError, Exception):
                continue

        if csv_content is None:
            return jsonify({
                "code": 500,
                "error": "无法读取CSV文件编码"
            }), 500

        # 返回原始文本
        response = make_response(csv_content)
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        return response

    except Exception as e:
        print(f"获取CSV文本失败: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 500,
            "error": f"服务器错误: {str(e)}"
        }), 500


@app.route("/sync-user-data", methods=["POST"]) #前端传数据→后端校验清洗→写入后端文件→更新推荐
def sync_user_data():
    try:
        # 解析前端数据
        data = None
        try:
            data = request.get_json(force=True)
        except:
            try:
                data = json.loads(request.data.decode('utf-8', errors='replace'))
            except Exception as e:
                print(f"JSON解析失败: {str(e)}")
                return jsonify({"code": 400, "error": "无效的JSON格式"}), 400

        # 验证数据结构
        if not isinstance(data, dict) or 'preferences' not in data:
            return jsonify({"code": 400, "error": "缺少preferences字段"}), 400

        preferences = data.get('preferences', [])
        if not isinstance(preferences, list):
            return jsonify({"code": 400, "error": "preferences必须是数组"}), 400

        # 验证并规范化偏好数据
        valid_preferences = []
        for i, item in enumerate(preferences):
            if not isinstance(item, dict):
                continue

            item_id = item.get('id', f"item_{i}")
            name = item.get('name', '') or item.get('title', f"未命名项目_{i}")
            genres = item.get('genres', [])

            if isinstance(genres, str):
                genres = [g.strip() for g in genres.split(',') if g.strip()]
            if not isinstance(genres, list) or not genres:
                continue

            # 保留更多信息用于增强推荐
            valid_preferences.append({
                'id': item_id,
                'name': name,
                'title': name,
                'genres': genres,
                'rating': item.get('rating', 0),
                'cover_url': item.get('cover_url', ''),
                'year': item.get('year', 0),
                'director': item.get('director', ''),
                'actors': item.get('actors', ''),
                'plot': item.get('plot', '')
            })

        print(f"验证后有效数据: {len(valid_preferences)} 条")
        if not valid_preferences:
            return jsonify({"code": 400, "error": "无有效偏好数据"}), 400

        # 更新用户数据并检查权重变化
        old_user_data = init_or_repair_user_data()
        old_weights = old_user_data.get('count_weights', {})
        new_weights = calculate_count_weights(valid_preferences)
        need_update = old_weights != new_weights

        # 保存用户数据
        user_data = old_user_data
        user_data['preferences'] = valid_preferences
        user_data['count_weights'] = new_weights
        user_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not safe_write_json(Config.USER_DATA_FILE, user_data):
            return jsonify({"code": 500, "error": "服务器写入文件失败"}), 500

        # 权重变化时强制更新推荐文件
        if need_update:
            generate_and_save_recommendations('movie')
            generate_and_save_recommendations('series')
            print(f"权重变化：{old_weights} → {new_weights}，已更新推荐文件")
        else:
            print("权重无变化，推荐文件未更新")

        return jsonify({
            "code": 0,
            "message": "数据同步成功",
            "count_weights": new_weights,
            "saved_preferences_count": len(valid_preferences),
            "updated_recommendations": need_update
        })

    except Exception as e:
        print(f"同步请求处理异常: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 500, "error": f"服务器内部错误: {str(e)}"}), 500


@app.route("/get_recommend", methods=["GET"])
def get_recommend():
    try:
        recommend_type = request.args.get('type', 'movie').lower()
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

        if recommend_type not in ['movie', 'series']:
            recommend_type = 'movie'

        # 强制刷新优先级最高
        need_refresh = force_refresh or refresh
        if not need_refresh:
            output_path = Config.RECOMMEND_OUTPUT_PATH[recommend_type]
            if os.path.exists(output_path):
                # 检查文件是否过期（5分钟）
                file_mtime = os.path.getmtime(output_path)
                file_age = datetime.now().timestamp() - file_mtime
                if file_age > 300:  # 5分钟
                    need_refresh = True
            else:
                need_refresh = True

        if need_refresh:
            generate_and_save_recommendations(recommend_type)

        # 读取推荐数据
        recommend_data = safe_read_json(Config.RECOMMEND_OUTPUT_PATH[recommend_type], {})
        recommendations = recommend_data.get("data", [])

        # 如果还是空的，直接读取CSV文件返回原始数据
        if not recommendations:
            csv_path = Config.DATASET_PATHS.get(recommend_type)
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path, encoding='utf-8')
                # 随机排序确保每次返回不同结果
                df = df.sample(frac=1).reset_index(drop=True)
                recommendations = df.head(10).to_dict('records')

        recommendations = [
            normalize_recommendation_item(item, recommend_type)
            for item in recommendations
            if isinstance(item, dict)
        ]

        user_data = init_or_repair_user_data()
        current_weights = recommend_data.get("count_weights")
        if not isinstance(current_weights, dict) or not {'genres', 'directors', 'actors'}.issubset(current_weights.keys()):
            current_weights = get_count_weights_for_type(user_data, recommend_type)

        current_weights = {
            "genres": sort_weight_map(current_weights.get("genres", {})),
            "directors": sort_weight_map(current_weights.get("directors", {})),
            "actors": sort_weight_map(current_weights.get("actors", {})),
        }
        recommend_reasons_summary = recommend_data.get("recommend_reasons_summary")
        if not isinstance(recommend_reasons_summary, list):
            recommend_reasons_summary = build_recommendation_reason_summary(
                get_preferences_for_type(user_data, recommend_type),
                current_weights,
                recommend_type,
            )

        return jsonify({
            "code": 0,
            "data": recommendations,
            "count_weights": current_weights,
            "recommend_reasons_summary": recommend_reasons_summary,
            "generated_time": recommend_data.get('generated_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            "refreshed": need_refresh,
            "algorithm_version": recommend_data.get('algorithm_version', "NCF+TextCNN_v1.0")
        })

    except Exception as e:
        print(f"获取推荐失败: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 500, "error": f"服务器错误: {str(e)}"}), 500


@app.route("/search", methods=["GET"])
def search():
    try:
        query = request.args.get('q', '').strip()#获取URL中？后面的参数
        content_type = request.args.get('type')

        if not query:
            return jsonify({"code": 400, "error": "缺少搜索关键词"}), 400

        results = smart_search(query, content_type)

        return jsonify({
            "code": 0,
            "query": query,
            "count": len(results),
            "results": results
        })

    except Exception as e:
        print(f"搜索失败: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 500, "error": f"服务器错误: {str(e)}"}), 500


@app.route("/negative-feedback", methods=["POST"])
def negative_feedback():
    try:
        data = request.get_json() or {}
        item_id = data.get('item_id')
        item_type = data.get('type', 'movie')
        reason = data.get('reason', '')

        if not item_id:
            return jsonify({"code": 400, "error": "缺少项目ID"}), 400

        recorded = add_negative_feedback(item_id, item_type, reason)

        # 立即更新推荐
        generate_and_save_recommendations(item_type)

        return jsonify({
            "code": 0,
            "message": "负反馈已记录",
            "item_id": item_id,
            "updated": True,
            "recorded": bool(recorded)
        })

    except Exception as e:
        print(f"负反馈处理失败: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 500, "error": f"服务器错误: {str(e)}"}), 500


# --------------------------
# 想看清单管理接口
# --------------------------
@app.route("/watchlist", methods=["GET"])
def get_watchlist():
    try:
        content_type = request.args.get('type')
        watchlist = manage_watchlist('get', None, content_type)

        return jsonify({
            "code": 0,
            "count": len(watchlist),
            "watchlist": watchlist,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        print(f"获取想看清单失败: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 500, "error": f"服务器错误: {str(e)}"}), 500


@app.route("/watchlist/add", methods=["POST"])
def add_to_watchlist():
    try:
        data = request.get_json() or {}
        item_id = data.get('item_id')
        item_type = data.get('type')
        item_data = data.get('data', {})

        if not item_id or not item_type:
            return jsonify({"code": 400, "error": "缺少必要参数"}), 400

        result = manage_watchlist('add', item_id, item_type, item_data)

        return jsonify({
            "code": 0,
            "message": result.get('message', '添加成功'),
            "item_id": item_id
        })

    except Exception as e:
        print(f"添加想看清单失败: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 500, "error": f"服务器错误: {str(e)}"}), 500


@app.route("/watchlist/remove", methods=["POST"])
def remove_from_watchlist():
    try:
        data = request.get_json() or {}
        item_id = data.get('item_id')
        item_type = data.get('type')

        if not item_id or not item_type:
            return jsonify({"code": 400, "error": "缺少必要参数"}), 400

        result = manage_watchlist('remove', item_id, item_type)

        return jsonify({
            "code": 0,
            "message": result.get('message', '移除成功'),
            "item_id": item_id
        })

    except Exception as e:
        print(f"移除想看清单失败: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 500, "error": f"服务器错误: {str(e)}"}), 500


@app.route("/watchlist/clear", methods=["POST"])
def clear_watchlist():
    try:
        data = request.get_json() or {}
        content_type = str(data.get('type', '')).strip().lower() or None
        result = manage_watchlist('clear', item_type=content_type)

        return jsonify({
            "code": 0,
            "message": result.get('message', 'watchlist_cleared'),
            "deleted_count": result.get('deleted_count', 0),
            "type": content_type or 'all'
        })

    except Exception as e:
        print(f"娓呯┖鎯崇湅娓呭崟澶辫触: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 500, "error": f"鏈嶅姟鍣ㄩ敊璇? {str(e)}"}), 500


@app.route("/refresh-recommendations", methods=["POST", "GET"])
def refresh_recommendations():
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = request.args

        content_type = data.get('type')

        if content_type:
            generate_and_save_recommendations(content_type)
            message = f"{content_type}推荐已刷新"
        else:
            generate_and_save_recommendations('movie')
            generate_and_save_recommendations('series')
            message = "所有推荐已刷新"

        return jsonify({
            "code": 0,
            "message": message,
            "type": content_type or "all",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        print(f"刷新推荐失败: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 500, "error": f"服务器错误: {str(e)}"}), 500


@app.route("/refresh-status", methods=["GET"])
def refresh_status():
    try:
        job_id = request.args.get('job_id', '').strip()
        if not job_id:
            return jsonify({"code": 400, "error": "missing_job_id"}), 400

        with refresh_jobs_lock:
            job = refresh_jobs.get(job_id)
            if not job:
                return jsonify({"code": 404, "error": "job_not_found"}), 404
            return jsonify({"code": 0, **job})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 500, "error": str(e)}), 500


def sync_user_data_v2():
    """Persist typed preferences and trigger background refresh jobs."""
    try:
        data = request.get_json(force=True)
        if not isinstance(data, dict) or 'preferences' not in data:
            return jsonify({"code": 400, "error": "missing_preferences"}), 400

        normalized_preferences = normalize_preferences_payload(data.get('preferences', []))
        total_preferences = len(normalized_preferences['movie']) + len(normalized_preferences['series'])

        user_data = init_or_repair_user_data()
        old_weights = user_data.get('count_weights', {})
        new_weights = {
            'movie': calculate_preference_weights(normalized_preferences['movie']),
            'series': calculate_preference_weights(normalized_preferences['series']),
        }
        if total_preferences == 0:
            clear_user_preferences('user_default')
        else:
            replace_user_preferences('user_default', normalized_preferences)
        user_data['preferences'] = normalized_preferences
        user_data['count_weights'] = new_weights
        user_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not safe_write_json(Config.USER_DATA_FILE, user_data):
            return jsonify({"code": 500, "error": "failed_to_write_user_data"}), 500

        jobs = {}
        if old_weights != new_weights:
            jobs['movie'] = start_refresh_job('movie')
            jobs['series'] = start_refresh_job('series')

        return jsonify({
            "code": 0,
            "message": "sync_success",
            "count_weights": new_weights,
            "saved_preferences_count": total_preferences,
            "updated_recommendations": bool(jobs),
            "jobs": jobs,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 500, "error": str(e)}), 500


@app.route("/user-preferences", methods=["GET"])
def get_user_preferences_route():
    """Return current typed user preferences from the database-backed source."""
    try:
        content_type = str(request.args.get('type', '')).strip().lower()
        if content_type and content_type not in ('movie', 'series'):
            return jsonify({"code": 400, "error": "invalid_type"}), 400

        user_data = init_or_repair_user_data()
        db_preferences = get_user_preferences('user_default', content_type or None)
        fallback_preferences = {
            "movie": get_preferences_for_type(user_data, 'movie'),
            "series": get_preferences_for_type(user_data, 'series'),
        }
        preferences = {
            "movie": db_preferences.get('movie') or fallback_preferences['movie'],
            "series": db_preferences.get('series') or fallback_preferences['series'],
        }
        count_weights = {
            "movie": get_count_weights_for_type(user_data, 'movie'),
            "series": get_count_weights_for_type(user_data, 'series'),
        }

        if content_type:
            return jsonify({
                "code": 0,
                "type": content_type,
                "preferences": preferences.get(content_type, []),
                "count_weights": count_weights.get(content_type, {}),
            })

        return jsonify({
            "code": 0,
            "preferences": preferences,
            "count_weights": count_weights,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 500, "error": str(e)}), 500


def get_recommend_v2():
    """Return cached recommendation results without synchronous regeneration."""
    try:
        recommend_type = request.args.get('type', 'movie').lower()
        if recommend_type not in ('movie', 'series'):
            recommend_type = 'movie'

        recommend_data = safe_read_json(Config.RECOMMEND_OUTPUT_PATH[recommend_type], {})
        recommendations = recommend_data.get("data", [])
        if not recommendations:
            csv_path = Config.DATASET_PATHS.get(recommend_type)
            if csv_path and os.path.exists(csv_path):
                df = safe_read_csv(csv_path)
                if not df.empty:
                    recommendations = df.sample(frac=1).reset_index(drop=True).head(10).to_dict('records')

        recommendations = [
            normalize_recommendation_item(item, recommend_type)
            for item in recommendations
            if isinstance(item, dict)
        ]

        user_data = init_or_repair_user_data()
        current_weights = recommend_data.get("count_weights")
        if not isinstance(current_weights, dict) or not {'genres', 'directors', 'actors'}.issubset(current_weights.keys()):
            current_weights = get_count_weights_for_type(user_data, recommend_type)

        current_weights = {
            "genres": sort_weight_map(current_weights.get("genres", {})),
            "directors": sort_weight_map(current_weights.get("directors", {})),
            "actors": sort_weight_map(current_weights.get("actors", {})),
        }
        recommend_reasons_summary = recommend_data.get("recommend_reasons_summary")
        if not isinstance(recommend_reasons_summary, list):
            recommend_reasons_summary = build_recommendation_reason_summary(
                get_preferences_for_type(user_data, recommend_type),
                current_weights,
                recommend_type,
            )

        return jsonify({
            "code": 0,
            "data": recommendations,
            "count_weights": current_weights,
            "recommend_reasons_summary": recommend_reasons_summary,
            "generated_time": recommend_data.get('generated_time', ''),
            "refreshed": False,
            "algorithm_version": recommend_data.get('algorithm_version', "NCF_TextCNN_v3.0")
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 500, "error": str(e)}), 500


def refresh_recommendations_v2():
    """Queue recommendation refresh jobs and return immediately."""
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = request.args

        content_type = str(data.get('type', '')).strip().lower()
        if content_type and content_type not in ('movie', 'series'):
            return jsonify({"code": 400, "error": "invalid_type"}), 400

        if content_type:
            recommend_data = safe_read_json(Config.RECOMMEND_OUTPUT_PATH[content_type], {})
            cached_signature = str(recommend_data.get('signature', '') or '')
            current_signature = get_current_recommendation_signature(content_type)
            if current_signature and cached_signature == current_signature:
                rotation_result = rotate_cached_recommendations(content_type)
                if not rotation_result.get('ok'):
                    job_id = start_refresh_job(content_type)
                    return jsonify({
                        "code": 0,
                        "message": "refresh_queued",
                        "type": content_type,
                        "job_id": job_id,
                        "status": "queued",
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                job_id = build_completed_refresh_job(content_type, reused=True)
                return jsonify({
                    "code": 0,
                    "message": "refresh_rotated" if rotation_result.get('ok') else "refresh_reused",
                    "type": content_type,
                    "job_id": job_id,
                    "status": "done",
                    "reused": True,
                    "rotated": bool(rotation_result.get('rotated')),
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            job_id = start_refresh_job(content_type)
            return jsonify({
                "code": 0,
                "message": "refresh_queued",
                "type": content_type,
                "job_id": job_id,
                "status": "queued",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        jobs = {}
        reused = {}
        for recommend_type in ('movie', 'series'):
            recommend_data = safe_read_json(Config.RECOMMEND_OUTPUT_PATH[recommend_type], {})
            cached_signature = str(recommend_data.get('signature', '') or '')
            current_signature = get_current_recommendation_signature(recommend_type)
            if current_signature and cached_signature == current_signature:
                rotation_result = rotate_cached_recommendations(recommend_type)
                if rotation_result.get('ok'):
                    jobs[recommend_type] = build_completed_refresh_job(recommend_type, reused=True)
                    reused[recommend_type] = True
                else:
                    jobs[recommend_type] = start_refresh_job(recommend_type)
                    reused[recommend_type] = False
            else:
                jobs[recommend_type] = start_refresh_job(recommend_type)
                reused[recommend_type] = False
        return jsonify({
            "code": 0,
            "message": "refresh_queued",
            "type": "all",
            "jobs": jobs,
            "reused": reused,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"code": 500, "error": str(e)}), 500


app.view_functions['sync_user_data'] = sync_user_data_v2
app.view_functions['get_recommend'] = get_recommend_v2
app.view_functions['refresh_recommendations'] = refresh_recommendations_v2


# --------------------------
# AI Recommendation Pipeline API
# --------------------------
@app.route("/api/ai/recommend/full", methods=["POST"])
def full_ai_recommend():
    """The main endpoint for the entire AI recommendation pipeline."""
    request_id = uuid.uuid4().hex[:8]
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 1) # Default to user 1 for demo
        query = data.get('query', '')
        logger.info(f"[ReqID: {request_id}] Received AI recommendation request for user_id={user_id}, query='{query}'")

        if not query:
            logger.warning(f"[ReqID: {request_id}] Query is empty.")
            return jsonify({"code": 400, "error": "Query is required"}), 400

        # Phase 1: Get decision from Agent
        agent_input = {
            "user_id": user_id,
            "query": query,
            "context": {"history": [] if user_id != 1 else [123]}
        }
        agent_decision = agent.decide(agent_input)
        logger.info(f"[ReqID: {request_id}] Agent decision: {agent_decision['intent']}, strategy: {agent_decision['strategy']}")

        # Phase 3: Get final recommendations from Orchestrator
        orchestrator_input = {"user_id": user_id, "query": query, "agent_decision": agent_decision}
        orchestrator_output = orchestrator.orchestrate(orchestrator_input)
        recommendations = orchestrator_output.get("recommendations", [])
        logger.info(f"[ReqID: {request_id}] Orchestrator returned {len(recommendations)} recommendations after fusion and filtering.")

        # Phase 5.1: Generate per-item explanations
        if settings.EXPLAIN_ENABLED:
            explanations = generate_per_item_explanations(recommendations)
            for item in recommendations:
                item["explanation"] = explanations.get(item["movie_id"], "为您推荐这部优质电影。")

        # Phase 5.2: Build debug trace
        debug_trace = None
        if settings.DEBUG_MODE_ENABLED:
            fusion_weights = get_fusion_weights(agent_decision, query)
            debug_trace = build_debug_trace(agent_decision, fusion_weights, orchestrator_output.get("raw_results", {}))
            logger.debug(f"[ReqID: {request_id}] Debug trace generated.")

        # Final response for the frontend
        final_response = {
            "recommendations": recommendations,
            "debug_trace": debug_trace
        }
        
        logger.info(f"[ReqID: {request_id}] Successfully processed request.")
        return jsonify({"code": 0, "data": final_response})

    except Exception as e:
        logger.error(f"[ReqID: {request_id}] AI Recommendation Pipeline failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"code": 500, "error": f"Server error: {str(e)}"}), 500


@app.route("/proxy-image", methods=["GET"])
def proxy_image_route():
    try:
        url = request.args.get("url")
        if not url:
            return jsonify({"code": 400, "error": "缺少图片URL"}), 400

        # 检查域名是否允许
        if 'is_allowed_domain' in globals() and not is_allowed_domain(url):
            return jsonify({"code": 403, "error": "图片域名不被允许"}), 403

        image_data = proxy_image(url)
        if not image_data:
            return jsonify({"code": 404, "error": "图片获取失败"}), 404

        # 获取文件类型
        img_type = detect_image_type(image_data)
        resp = make_response(image_data)
        resp.headers["Content-Type"] = f"image/{img_type}"
        resp.headers["Cache-Control"] = "public, max-age=86400"  # 缓存1天

        return resp

    except Exception as e:
        print(f"图片代理失败: {str(e)}")
        return jsonify({"code": 500, "error": f"服务器错误: {str(e)}"}), 500


# --------------------------
# 电影查询接口
# --------------------------
@app.route("/api/get-movie-by-name", methods=["POST"])
def get_movie_by_name():
    """根据电影名称查询详细信息"""
    try:
        data = request.get_json() or {}
        movie_name = data.get('name', '').strip()

        if not movie_name:
            return jsonify({
                "code": 400,
                "error": "缺少电影名称参数"
            }), 400

        result, error = search_item_by_name(movie_name, 'movie')

        if error:
            return jsonify({
                "code": 404,
                "error": f"未找到电影: {movie_name} ({error})"
            }), 404

        return jsonify({
            "code": 0,
            "data": result
        })

    except Exception as e:
        print(f"查询电影失败: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 500,
            "error": f"服务器错误: {str(e)}"
        }), 500


@app.route("/api/get-movies-by-names", methods=["POST"])
def get_movies_by_names():
    """批量查询电影信息"""
    try:
        data = request.get_json() or {}
        movie_names = data.get('names', [])
        only_return_requested = data.get('onlyReturnRequested', True)

        if not isinstance(movie_names, list) or len(movie_names) == 0:
            return jsonify({
                "code": 400,
                "error": "电影名称列表不能为空"
            }), 400

        search_results = batch_search_items_by_names(movie_names, 'movie')
        results = search_results if only_return_requested else [item for item in search_results if item.get('data')]

        return jsonify({
            'code': 0,
            'results': results,
            'count': len(results),
            'success_count': len([r for r in results if r.get('data')])
        })

    except Exception as e:
        print(f"批量查询电影失败: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'code': 500,
            'error': f"服务器错误: {str(e)}",
            'results': []
        }), 500


# --------------------------
# 剧集查询接口
# --------------------------
@app.route("/api/get-drama-by-name", methods=["POST"])
@app.route("/api/get-series-by-name", methods=["POST"])
def get_drama_by_name():
    """根据剧集名称查询详细信息"""
    try:
        data = request.get_json() or {}
        drama_name = data.get('name', '').strip()

        if not drama_name:
            return jsonify({
                "code": 400,
                "error": "缺少剧集名称参数"
            }), 400

        result, error = search_item_by_name(drama_name, 'series')

        if error:
            return jsonify({
                "code": 404,
                "error": f"未找到剧集: {drama_name} ({error})"
            }), 404

        return jsonify({
            "code": 0,
            "data": result
        })

    except Exception as e:
        print(f"查询剧集失败: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 500,
            "error": f"服务器错误: {str(e)}"
        }), 500


@app.route("/api/get-dramas-by-names", methods=["POST"])
@app.route("/api/get-series-by-names", methods=["POST"])
def get_dramas_by_names():
    """批量查询剧集信息"""
    try:
        data = request.get_json() or {}
        drama_names = data.get('names', [])
        only_return_requested = data.get('onlyReturnRequested', True)

        if not isinstance(drama_names, list) or len(drama_names) == 0:
            return jsonify({
                "code": 400,
                "error": "剧集名称列表不能为空"
            }), 400

        search_results = batch_search_items_by_names(drama_names, 'series')
        results = search_results if only_return_requested else [item for item in search_results if item.get('data')]

        return jsonify({
            'code': 0,
            'results': results,
            'count': len(results),
            'success_count': len([r for r in results if r.get('data')])
        })

    except Exception as e:
        print(f"批量查询剧集失败: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'code': 500,
            'error': f"服务器错误: {str(e)}",
            'results': []
        }), 500


# --------------------------
# 系统信息接口
# --------------------------
@app.route("/api/system-info", methods=["GET"])
def system_info():
    """获取系统信息"""
    try:
        user_data = init_or_repair_user_data()
        preferences_count = sum(
            len(user_data.get('preferences', {}).get(content_type, []) or [])
            for content_type in ('movie', 'series')
        )
        return jsonify({
            "code": 0,
            "server_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "base_dir": Config.BASE_DIR,
            "preferences_count": preferences_count,
            "movie_dataset_exists": os.path.exists(Config.DATASET_PATHS['movie']),
            "series_dataset_exists": os.path.exists(Config.DATASET_PATHS['series']),
            "api_version": "v2.0"
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "error": str(e)
        }), 500


# --------------------------
# Frontend Serving
# --------------------------
@app.route("/")
def serve_frontend():
    """Serves the main frontend HTML file."""
    return send_file(os.path.join(os.path.dirname(PACKAGE_ROOT), 'frontend', 'index.html'))

@app.route("/<path:filename>")
def serve_static_files(filename):
    """Serves static files like CSS and JS."""
    return send_file(os.path.join(os.path.dirname(PACKAGE_ROOT), 'frontend', filename))


# --------------------------
# 启动服务
# --------------------------
if __name__ == "__main__":
    # 确保数据目录存在
    os.makedirs(os.path.join(Config.BASE_DIR, 'data'), exist_ok=True)

    init_or_repair_user_data()
    print(f"工作目录: {Config.BASE_DIR}")
    print("初始化推荐文件...")

    # 静默初始化推荐文件
    try:
        generate_and_save_recommendations('movie')
        generate_and_save_recommendations('series')
    except Exception as e:
        print(f"初始化推荐文件警告: {e}")

    # 启动Flask应用
    # host='0.0.0.0' 使其可以从本地网络访问
    app.run(host='0.0.0.0', port=5000, debug=True)
