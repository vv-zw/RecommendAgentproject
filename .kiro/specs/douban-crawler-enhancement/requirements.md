# 需求文档

## 简介

本功能旨在增强现有影视推荐系统的豆瓣数据爬取能力。当前数据集（`douban_movies.csv` / `douban_series.csv`）仅包含 7 个基础字段，导致 `content_items` 表中的导演、主演、剧情简介、地区、语言、时长、集数等字段全部为空，前端详情页（MovieDetail.tsx / SeriesDetail.tsx）因此无法展示完整信息。

本功能将按以下顺序执行：
1. **验证并确认数据表字段完整性** — 爬取前先检查 `content_items` 表是否包含所有目标字段，若缺失则自动补充（`ALTER TABLE ADD COLUMN IF NOT EXISTS`）
2. **实现 Python 爬虫模块** — 从豆瓣网页爬取完整影片/剧集详情字段
3. **定时自动写入数据库** — 通过定时任务将数据 upsert 到 PostgreSQL，同时支持手动触发和完整日志记录

---

## 词汇表

- **Crawler（爬虫）**：负责从豆瓣网页抓取影片/剧集详情数据的 Python 模块
- **Scheduler（调度器）**：负责按配置时间间隔自动触发爬虫任务的定时任务组件
- **DetailFetcher（详情抓取器）**：负责请求单个豆瓣条目页面并解析 HTML 的子组件
- **DataWriter（数据写入器）**：负责将爬取结果 upsert 到 PostgreSQL `content_items` 表的子组件
- **CrawlLogger（爬取日志器）**：负责记录爬取进度、成功/失败数量及错误信息的日志组件
- **SchemaValidator（表结构验证器）**：爬取任务启动前负责检查并补全 `content_items` 表字段的组件
- **content_items**：PostgreSQL 数据库中存储影片/剧集信息的主表，位于 `app` schema
- **raw_source**：`content_items` 表中的 JSONB 字段，用于存储扩展数据（含热评列表 `reviews` 子键）
- **source_item_id**：豆瓣条目的唯一 ID，用于 upsert 时的冲突检测键
- **User-Agent 轮换**：每次 HTTP 请求随机选用不同的浏览器标识字符串，以规避豆瓣反爬检测

---

## 需求

### 需求 0：爬取前验证并确认数据表字段完整性

**用户故事：** 作为系统管理员，我希望爬虫在启动前自动检查数据库表结构，确保所有目标字段都存在，以便爬取的数据能完整写入，不因字段缺失导致数据丢失。

#### 验收标准

1. WHEN Crawler 启动时（无论是定时触发还是手动触发），THE SchemaValidator SHALL 在开始爬取前连接数据库，检查 `app.content_items` 表是否包含以下所有字段：`director`、`actors`、`year`、`region`、`language`、`duration`、`episodes`、`plot`、`raw_source`
2. WHEN SchemaValidator 发现某个字段不存在，THE SchemaValidator SHALL 自动执行 `ALTER TABLE app.content_items ADD COLUMN IF NOT EXISTS` 补充该字段，并记录一条 INFO 级别日志说明补充了哪个字段
3. WHEN SchemaValidator 完成所有字段检查，THE SchemaValidator SHALL 记录一条 INFO 级别日志，说明表结构验证通过，可以开始爬取
4. IF SchemaValidator 执行 ALTER TABLE 时发生数据库异常，THEN THE Crawler SHALL 终止本次爬取任务并记录 ERROR 级别日志，不继续爬取
5. THE SchemaValidator SHALL 确保 `raw_source` 字段为 JSONB 类型；若该字段已存在但类型不符，THE SchemaValidator SHALL 记录 WARNING 日志并继续（不强制修改已有字段类型）

### 需求 1：爬取影片/剧集完整详情字段

**用户故事：** 作为系统管理员，我希望爬虫能从豆瓣抓取每部影片/剧集的完整详情字段，以便前端详情页能展示导演、主演、剧情简介等完整信息。

#### 验收标准

1. WHEN DetailFetcher 请求豆瓣条目页面成功，THE DetailFetcher SHALL 解析并返回以下字段：导演（director）、主演前5位（actors）、上映/首播年份（year）、制片地区（region）、语言（language）、时长（duration，仅电影）、集数（episodes，仅剧集）、剧情简介（plot）
2. WHEN DetailFetcher 解析主演列表，THE DetailFetcher SHALL 最多提取前5位主演姓名，并以 "/" 分隔拼接为字符串
3. WHEN DetailFetcher 解析导演列表，THE DetailFetcher SHALL 提取所有导演姓名，并以 "/" 分隔拼接为字符串
4. WHEN DetailFetcher 解析上映年份，THE DetailFetcher SHALL 提取4位数字年份并转换为整数类型
5. WHEN DetailFetcher 请求豆瓣条目页面成功，THE DetailFetcher SHALL 解析并返回前5条热评，每条热评包含：作者用户名（author）、评论内容（content）、评分（rating，整数1-5）、日期（date，格式 "YYYY-MM-DD"）
6. WHEN DetailFetcher 解析热评评分，IF 评分字段缺失或无法解析，THEN THE DetailFetcher SHALL 将该条热评的 rating 字段设为 null
7. WHEN DetailFetcher 解析某个可选字段（如 duration、episodes、region）时页面中该字段不存在，THE DetailFetcher SHALL 将该字段返回为 null，不影响其他字段的解析

### 需求 2：反爬机制应对

**用户故事：** 作为系统管理员，我希望爬虫能有效应对豆瓣的反爬机制，以便爬取任务能稳定运行而不被封禁。

#### 验收标准

1. WHEN DetailFetcher 发起每次 HTTP 请求，THE DetailFetcher SHALL 在请求头中随机选用一个 User-Agent 字符串，User-Agent 池中至少包含5个不同的主流浏览器标识
2. WHEN DetailFetcher 完成一次条目页面请求后，THE DetailFetcher SHALL 等待1到3秒的随机延迟后再发起下一次请求
3. WHEN DetailFetcher 请求豆瓣页面失败（HTTP 错误或网络异常），THE DetailFetcher SHALL 最多重试3次，每次重试前等待的时间为上次等待时间的2倍（指数退避），初始等待时间为2秒
4. IF DetailFetcher 在3次重试后仍然失败，THEN THE DetailFetcher SHALL 返回失败结果并记录错误信息，不再继续重试该条目
5. WHEN DetailFetcher 收到 HTTP 429（Too Many Requests）响应，THE DetailFetcher SHALL 额外等待60秒后再重试

### 需求 3：数据写入数据库

**用户故事：** 作为系统管理员，我希望爬取的数据能自动写入 PostgreSQL 数据库，以便前端能立即读取最新数据。

#### 验收标准

1. WHEN DataWriter 接收到一批爬取结果，THE DataWriter SHALL 使用 psycopg3 将数据 upsert 到 `app.content_items` 表，以 `(source_item_id, content_type)` 为冲突检测键
2. WHEN DataWriter 执行 upsert 时发现记录已存在，THE DataWriter SHALL 更新以下字段：director、actors、year、region、language、duration、episodes、plot、raw_source、updated_at
3. WHEN DataWriter 执行 upsert 时发现记录不存在，THE DataWriter SHALL 插入完整的新记录
4. WHEN DataWriter 将热评数据写入数据库，THE DataWriter SHALL 将热评列表以 JSON 格式存入 `raw_source` 字段的 `reviews` 键，格式为 `[{"author": "用户名", "content": "评论内容", "rating": 4, "date": "2024-01-01"}]`
5. IF DataWriter 写入单条记录时发生数据库异常，THEN THE DataWriter SHALL 记录该条目的错误信息并继续处理下一条记录，不回滚整批写入

### 需求 4：定时自动爬取

**用户故事：** 作为系统管理员，我希望爬虫能按计划自动运行，以便数据库中的影片详情数据保持最新状态，无需人工干预。

#### 验收标准

1. THE Scheduler SHALL 支持通过配置文件或环境变量设置定时爬取的 cron 表达式，默认值为每天凌晨2点（`0 2 * * *`）
2. WHEN Scheduler 到达配置的触发时间，THE Scheduler SHALL 自动启动一次完整的爬取任务，覆盖 `content_items` 表中所有已有记录的 `source_item_id`
3. WHEN Scheduler 触发爬取任务时上一次爬取任务仍在运行，THE Scheduler SHALL 跳过本次触发并记录一条警告日志
4. THE Crawler SHALL 支持通过命令行参数 `--run-now` 手动触发一次立即爬取，不等待定时调度
5. THE Crawler SHALL 支持通过命令行参数 `--type`（可选值：`movie`、`series`、`all`，默认 `all`）指定本次爬取的内容类型
6. THE Crawler SHALL 支持通过命令行参数 `--limit N` 限制本次爬取的最大条目数量，用于测试场景

### 需求 5：日志记录

**用户故事：** 作为系统管理员，我希望爬取过程有完整的日志记录，以便监控爬取进度并排查失败原因。

#### 验收标准

1. WHEN Crawler 开始一次爬取任务，THE CrawlLogger SHALL 记录任务开始时间、目标内容类型和待爬取条目总数
2. WHEN DetailFetcher 成功爬取并解析一个条目，THE CrawlLogger SHALL 记录该条目的 source_item_id、标题和耗时
3. WHEN DetailFetcher 爬取某个条目失败（重试耗尽后），THE CrawlLogger SHALL 记录该条目的 source_item_id、失败原因和重试次数
4. WHEN Crawler 完成一次爬取任务，THE CrawlLogger SHALL 记录任务结束时间、成功条目数、失败条目数和总耗时
5. THE CrawlLogger SHALL 将日志同时输出到控制台和日志文件，日志文件路径为 `logs/crawler.log`，日志级别可通过环境变量 `LOG_LEVEL` 配置
6. WHEN 日志文件大小超过10MB，THE CrawlLogger SHALL 自动轮转日志文件，最多保留5个历史日志文件

### 需求 6：爬取任务的健壮性

**用户故事：** 作为系统管理员，我希望单个条目的爬取失败不影响整体任务，以便爬取任务能尽可能多地完成数据更新。

#### 验收标准

1. WHEN DetailFetcher 爬取某个条目时发生任何未预期异常，THE Crawler SHALL 捕获该异常，记录错误日志，并继续爬取下一个条目
2. WHEN Crawler 完成全部条目的爬取，IF 存在失败条目，THEN THE CrawlLogger SHALL 在任务结束日志中列出所有失败条目的 source_item_id 列表
3. THE Crawler SHALL 支持通过命令行参数 `--retry-failed` 仅重新爬取上次任务中失败的条目，失败列表从日志或持久化文件中读取
