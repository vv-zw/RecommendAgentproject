# crawler/utils.py
"""工具函数：User-Agent 池、随机延迟、指数退避重试装饰器、Playwright 页面获取"""

import random
import time
import functools
import logging
import os
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable)

# 从环境变量读取豆瓣 Cookie（可选，有则优先使用）
DOUBAN_COOKIE = os.getenv("DOUBAN_COOKIE", "")

# ── User-Agent 池（6个主流浏览器标识）────────────────────────────
USER_AGENTS = [
    # Chrome / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
    "Gecko/20100101 Firefox/121.0",
    # Safari / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Chrome / Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Edge / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


def random_ua() -> str:
    """从 User-Agent 池中随机返回一个 UA 字符串。"""
    return random.choice(USER_AGENTS)


def random_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    """随机等待 [min_s, max_s] 秒，模拟人工浏览行为。"""
    delay = random.uniform(min_s, max_s)
    logger.debug(f"随机延迟 {delay:.2f} 秒")
    time.sleep(delay)


def retry_with_backoff(max_retries: int = 3, base_delay: float = 2.0):
    """
    指数退避重试装饰器。
    - 第 n 次重试前等待 base_delay * 2^(n-1) 秒
    - HTTP 429 时额外等待 60 秒
    - 超过 max_retries 次后抛出最后一次异常
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt >= max_retries:
                        logger.warning(
                            f"{func.__name__} 重试耗尽（{max_retries}次），最终失败：{exc}"
                        )
                        raise

                    wait = base_delay * (2 ** attempt)

                    # HTTP 429 额外等待 60 秒
                    exc_str = str(exc)
                    if "429" in exc_str:
                        logger.warning(f"收到 HTTP 429，额外等待 60 秒后重试")
                        time.sleep(60)
                    else:
                        logger.warning(
                            f"{func.__name__} 第 {attempt + 1} 次失败：{exc}，"
                            f"{wait:.1f} 秒后重试"
                        )
                        time.sleep(wait)

            raise last_exc  # 不会到达，但让类型检查器满意
        return wrapper  # type: ignore
    return decorator


def build_headers(referer: str = "https://movie.douban.com/") -> dict:
    """构建请求头，包含随机 UA 和必要的 Cookie。"""
    import random
    import string
    # 生成随机 bid（豆瓣反爬 cookie）
    bid = ''.join(random.choices(string.ascii_letters + string.digits, k=11))
    return {
        "User-Agent": random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": referer,
        "Connection": "keep-alive",
        "Cookie": f"bid={bid}; ll=\"108288\"; _pk_id.100001.4cf6=1; __utma=30149280.1.1700000000.1700000000.1700000000.1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    }


# ── Playwright 页面获取器 ─────────────────────────────────────────

class PlaywrightFetcher:
    """
    使用 Playwright 无头浏览器获取豆瓣页面 HTML。
    解决豆瓣对纯 requests 请求返回 JS 渲染空壳页面的问题。

    使用方式（上下文管理器）：
        with PlaywrightFetcher() as fetcher:
            html = fetcher.get_html("https://movie.douban.com/subject/1234567/")
    """

    # 等待页面加载完成的选择器（豆瓣详情页核心区块）
    DETAIL_READY_SELECTOR = "#info"
    COMMENTS_READY_SELECTOR = "div#comments"

    # 页面加载超时（毫秒）
    PAGE_TIMEOUT = 30_000
    # 等待选择器超时（毫秒）
    SELECTOR_TIMEOUT = 15_000

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._playwright = None
        self._browser = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        return self

    def __exit__(self, *_):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def get_html(self, url: str, wait_selector: Optional[str] = None) -> Optional[str]:
        """
        用 Playwright 打开 URL，等待目标选择器出现后返回完整 HTML。
        失败时返回 None。
        """
        if self._browser is None:
            raise RuntimeError("PlaywrightFetcher 未初始化，请使用 with 语句")

        context = self._browser.new_context(
            user_agent=random_ua(),
            locale="zh-CN",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": "https://movie.douban.com/",
            },
        )

        # 注入 Cookie（如果配置了真实 Cookie）
        if DOUBAN_COOKIE:
            _inject_cookies(context, DOUBAN_COOKIE)

        page = context.new_page()

        # 隐藏 webdriver 特征
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        try:
            page.goto(url, timeout=self.PAGE_TIMEOUT, wait_until="domcontentloaded")

            # 等待目标内容区块出现
            selector = wait_selector or self.DETAIL_READY_SELECTOR
            try:
                page.wait_for_selector(selector, timeout=self.SELECTOR_TIMEOUT)
            except Exception:
                # 选择器未出现（可能是评论页或其他页面），仍返回当前 HTML
                logger.debug(f"选择器 {selector} 未在 {url} 中找到，返回当前页面 HTML")

            html = page.content()
            return html

        except Exception as e:
            logger.warning(f"Playwright 获取页面失败 [{url}]：{e}")
            return None
        finally:
            page.close()
            context.close()


def _inject_cookies(context, cookie_str: str) -> None:
    """将 'key=value; key2=value2' 格式的 Cookie 字符串注入 Playwright context。"""
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".douban.com",
                "path": "/",
            })
    if cookies:
        context.add_cookies(cookies)
