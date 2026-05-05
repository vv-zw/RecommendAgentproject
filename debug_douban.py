"""调试豆瓣页面结构，使用 Playwright 无头浏览器绕过 JS 渲染反爬，打印 #info 区块的实际 HTML"""
from bs4 import BeautifulSoup
from crawler.utils import PlaywrightFetcher

url = "https://movie.douban.com/subject/36934908/"

print(f"正在用 Playwright 获取：{url}")
print("（首次启动浏览器可能需要几秒）\n")

with PlaywrightFetcher() as pw:
    html = pw.get_html(url, wait_selector="#info")

if not html:
    print("❌ 获取失败，html 为 None")
    exit(1)

soup = BeautifulSoup(html, "html.parser")

# 页面标题
title = soup.find("title")
print(f"页面标题: {title.get_text() if title else '无'}")

# v:itemreviewed（片名）
item_reviewed = soup.find("span", property="v:itemreviewed")
print(f"v:itemreviewed: {item_reviewed.get_text() if item_reviewed else '未找到'}")

# #info 区块
info_div = soup.find("div", id="info")
if info_div:
    print("\n=== #info 区块内容（前3000字符）===")
    print(info_div.prettify()[:3000])
else:
    print("\n❌ 未找到 #info 区块！")
    print("\n页面前800字符:")
    print(html[:800])

# 年份
year_span = soup.find("span", class_="year")
print(f"\n年份: {year_span.get_text() if year_span else '未找到'}")

# 剧情简介
plot = soup.find("span", property="v:summary")
if plot:
    print(f"\n剧情简介（前200字）: {plot.get_text(strip=True)[:200]}")
else:
    print("\n剧情简介: 未找到")
