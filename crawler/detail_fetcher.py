# crawler/detail_fetcher.py
"""
DetailFetcher：使用 Playwright 无头浏览器请求豆瓣条目详情页和热评页，
解析 HTML 提取完整字段。Playwright 可绕过豆瓣 JS 渲染反爬机制。
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from crawler.utils import build_headers, random_delay, PlaywrightFetcher

logger = logging.getLogger("crawler.fetcher")

DOUBAN_DETAIL_URL = "https://movie.douban.com/subject/{id}/"
DOUBAN_COMMENTS_URL = "https://movie.douban.com/subject/{id}/comments?status=P&sort=new_score"

REQUEST_TIMEOUT = 15  # 秒（requests 备用方案）


@dataclass
class ReviewItem:
    author: str
    content: str
    rating: Optional[int]   # 1-5，缺失时为 None
    date: Optional[str]     # YYYY-MM-DD


@dataclass
class FetchResult:
    source_item_id: str
    content_type: str
    title: Optional[str] = None
    director: Optional[str] = None
    actors: Optional[str] = None
    year: Optional[int] = None
    region: Optional[str] = None
    language: Optional[str] = None
    duration: Optional[str] = None
    episodes: Optional[str] = None
    plot: Optional[str] = None
    reviews: List[ReviewItem] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    retries: int = 0


class DetailFetcher:
    """从豆瓣爬取单个条目的完整详情字段。使用 Playwright 无头浏览器绕过 JS 渲染反爬。"""

    MAX_RETRIES = 3
    BASE_DELAY = 2.0   # 指数退避基础延迟（秒）
    RATE_LIMIT_WAIT = 60  # HTTP 429 额外等待（秒）

    def fetch(self, source_item_id: str, content_type: str) -> FetchResult:
        """
        爬取单个条目，内部处理重试逻辑。
        返回 FetchResult，失败时 success=False。
        """
        result = FetchResult(
            source_item_id=source_item_id,
            content_type=content_type,
        )

        detail_url = DOUBAN_DETAIL_URL.format(id=source_item_id)
        comments_url = DOUBAN_COMMENTS_URL.format(id=source_item_id)

        # ── 使用 Playwright 爬取（带重试）────────────────────────
        with PlaywrightFetcher() as pw:
            detail_html = self._fetch_with_retry_pw(
                pw, detail_url, result,
                wait_selector="#info",
            )
            if detail_html is None:
                return result  # 已标记 success=False

            # ── 解析详情页 ─────────────────────────────────────────
            try:
                parsed = self._parse_detail(detail_html, content_type)
                result.title    = parsed.get("title")
                result.director = parsed.get("director")
                result.actors   = parsed.get("actors")
                result.year     = parsed.get("year")
                result.region   = parsed.get("region")
                result.language = parsed.get("language")
                result.duration = parsed.get("duration")
                result.episodes = parsed.get("episodes")
                result.plot     = parsed.get("plot")
            except Exception as e:
                logger.warning(f"[{source_item_id}] 详情页解析异常：{e}")
                # 解析失败不终止，继续爬热评

            # ── 随机延迟后爬取热评页 ───────────────────────────────
            random_delay()
            comments_html = self._fetch_with_retry_pw(
                pw, comments_url, result,
                wait_selector="div#comments",
                is_comments=True,
            )
            if comments_html:
                try:
                    result.reviews = self._parse_reviews(comments_html)
                except Exception as e:
                    logger.warning(f"[{source_item_id}] 热评页解析异常：{e}")

        return result

    # ── 内部方法 ──────────────────────────────────────────────────

    def _fetch_with_retry_pw(
        self,
        pw: PlaywrightFetcher,
        url: str,
        result: FetchResult,
        wait_selector: str = "#info",
        is_comments: bool = False,
    ) -> Optional[str]:
        """使用 Playwright 带指数退避重试获取页面 HTML。"""
        last_exc: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                html = pw.get_html(url, wait_selector=wait_selector)
                if html is None:
                    raise RuntimeError("Playwright 返回空页面")

                # 检测是否被反爬（返回纯豆瓣首页 JS 空壳）
                if "<title>豆瓣</title>" in html and "id=\"info\"" not in html:
                    raise RuntimeError("疑似被反爬拦截，返回了豆瓣首页")

                return html

            except Exception as e:
                last_exc = e
                if attempt >= self.MAX_RETRIES:
                    break
                wait = self.BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"[{result.source_item_id}] 第 {attempt + 1} 次失败：{e}，"
                    f"{wait:.1f}s 后重试"
                )
                result.retries = attempt + 1
                time.sleep(wait)

        msg = f"重试 {self.MAX_RETRIES} 次后仍失败：{last_exc}"
        logger.error(f"[{result.source_item_id}] {msg}")
        if not is_comments:
            result.success = False
            result.error = msg
        return None

    def _fetch_with_retry(
        self,
        url: str,
        result: FetchResult,
        is_comments: bool = False,
    ) -> Optional[str]:
        """备用：带指数退避重试的 HTTP GET（requests），返回 HTML 字符串或 None。"""
        last_exc: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                resp = requests.get(
                    url,
                    headers=build_headers(referer="https://movie.douban.com/"),
                    timeout=REQUEST_TIMEOUT,
                )

                if resp.status_code == 429:
                    logger.warning(
                        f"[{result.source_item_id}] HTTP 429，等待 {self.RATE_LIMIT_WAIT}s"
                    )
                    time.sleep(self.RATE_LIMIT_WAIT)
                    continue

                if resp.status_code in (403, 404):
                    msg = f"HTTP {resp.status_code}，跳过该条目"
                    logger.warning(f"[{result.source_item_id}] {msg}")
                    if not is_comments:
                        result.success = False
                        result.error = msg
                    return None

                resp.raise_for_status()
                return resp.text

            except requests.RequestException as e:
                last_exc = e
                if attempt >= self.MAX_RETRIES:
                    break
                wait = self.BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"[{result.source_item_id}] 第 {attempt + 1} 次失败：{e}，"
                    f"{wait:.1f}s 后重试"
                )
                result.retries = attempt + 1
                time.sleep(wait)

        msg = f"重试 {self.MAX_RETRIES} 次后仍失败：{last_exc}"
        logger.error(f"[{result.source_item_id}] {msg}")
        if not is_comments:
            result.success = False
            result.error = msg
        return None

    def _parse_detail(self, html: str, content_type: str) -> dict:
        """解析豆瓣详情页 HTML，提取各字段。"""
        soup = BeautifulSoup(html, "html.parser")
        data: dict = {}

        # 调试：检查是否被反爬重定向到验证页面
        page_title = soup.find("title")
        page_title_text = page_title.get_text(strip=True) if page_title else ""
        logger.debug(f"页面标题：{page_title_text}")

        # 检测反爬：正常详情页标题格式为 "片名 (年份) - 豆瓣电影"
        if page_title_text in ("豆瓣", "豆瓣电影", "Douban") or not page_title_text:
            logger.warning(f"疑似被反爬拦截，页面标题：{page_title_text}")
            return data

        # ── 片名 ──────────────────────────────────────────────────
        title_tag = soup.find("span", property="v:itemreviewed")
        if title_tag:
            data["title"] = title_tag.get_text(strip=True)
        else:
            if page_title_text:
                title_from_page = page_title_text.split("(")[0].strip()
                if title_from_page and "豆瓣" not in title_from_page:
                    data["title"] = title_from_page
                    logger.debug(f"从页面标题提取片名：{title_from_page}")

        # ── #info 区块 ────────────────────────────────────────────
        info_div = soup.find("div", id="info")
        if not info_div:
            logger.warning("未找到 #info 区块，可能页面未完全加载")
            return data

        # 辅助函数：根据 span.pl 的文字找到后续文本
        def get_info_text(label: str) -> Optional[str]:
            for span in info_div.find_all("span", class_="pl"):
                if label in span.get_text():
                    attrs_span = span.find_next_sibling("span", class_="attrs")
                    if attrs_span:
                        return attrs_span.get_text(strip=True)
                    next_sib = span.next_sibling
                    if next_sib:
                        text = str(next_sib).strip().lstrip(":：").strip()
                        if text:
                            return text
            return None

        def get_info_links(label: str) -> List[str]:
            """获取某个标签后 span.attrs 中所有 <a> 的文本。"""
            for span in info_div.find_all("span", class_="pl"):
                if label in span.get_text():
                    attrs_span = span.find_next_sibling("span", class_="attrs")
                    if attrs_span:
                        return [a.get_text(strip=True) for a in attrs_span.find_all("a")]
            return []

        # ── 导演 ──────────────────────────────────────────────────
        directors = get_info_links("导演")
        if directors:
            data["director"] = "/".join(directors)

        # ── 主演（前5位）─────────────────────────────────────────
        actors_all: List[str] = []
        for span in info_div.find_all("span", class_="actor"):
            attrs = span.find("span", class_="attrs")
            if attrs:
                actors_all = [a.get_text(strip=True) for a in attrs.find_all("a")]
                break
        if actors_all:
            data["actors"] = "/".join(actors_all[:5])

        # ── 年份 ──────────────────────────────────────────────────
        year_span = soup.find("span", class_="year")
        if year_span:
            m = re.search(r"\d{4}", year_span.get_text())
            if m:
                data["year"] = int(m.group())

        # ── 制片地区 ──────────────────────────────────────────────
        region = get_info_text("制片国家/地区")
        if region:
            data["region"] = region.split("/")[0].strip()

        # ── 语言 ──────────────────────────────────────────────────
        language = get_info_text("语言")
        if language:
            data["language"] = language.split("/")[0].strip()

        # ── 时长（电影）/ 集数（剧集）────────────────────────────
        if content_type == "movie":
            duration = get_info_text("片长")
            if duration:
                data["duration"] = duration
        else:
            episodes = get_info_text("集数")
            if episodes:
                data["episodes"] = episodes.strip()

        # ── 剧情简介 ──────────────────────────────────────────────
        plot_span = soup.find("span", property="v:summary")
        if not plot_span:
            related = soup.find("div", class_="related-info")
            if related:
                indent = related.find("div", class_="indent")
                if indent:
                    plot_span = indent.find("span", class_="all") or indent

        if plot_span:
            data["plot"] = plot_span.get_text(strip=True)

        return data

    def _parse_reviews(self, html: str) -> List[ReviewItem]:
        """解析豆瓣热评页 HTML，返回前5条热评。"""
        soup = BeautifulSoup(html, "html.parser")
        reviews: List[ReviewItem] = []

        comment_items = soup.select("div#comments div.comment-item")
        for item in comment_items[:5]:
            # 作者
            avatar_a = item.select_one(".avatar a")
            author = avatar_a.get("title", "").strip() if avatar_a else "匿名"

            # 评论内容
            short_span = item.select_one(".comment-content span.short")
            content = short_span.get_text(strip=True) if short_span else ""

            # 评分（allstar10~allstar50）
            rating: Optional[int] = None
            rating_span = item.find(
                "span",
                class_=lambda c: c and c.startswith("allstar"),
            )
            if rating_span:
                cls_list = [
                    c for c in rating_span.get("class", [])
                    if c.startswith("allstar")
                ]
                if cls_list:
                    try:
                        rating = int(cls_list[0].replace("allstar", "")) // 10
                    except ValueError:
                        rating = None

            # 日期
            date: Optional[str] = None
            time_span = item.select_one(".comment-time")
            if time_span:
                m = re.search(r"\d{4}-\d{2}-\d{2}", time_span.get_text())
                if m:
                    date = m.group()

            if content:
                reviews.append(ReviewItem(
                    author=author,
                    content=content,
                    rating=rating,
                    date=date,
                ))

        return reviews
