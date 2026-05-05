# 实现任务列表：douban-crawler-enhancement

## 任务

- [x] 1. 创建 crawler 模块基础结构
  - [x] 1.1 创建 crawler/__init__.py
  - [x] 1.2 创建 crawler/utils.py（UA池、随机延迟、指数退避重试装饰器）
  - [x] 1.3 创建 crawler/crawl_logger.py（日志配置，控制台+文件轮转）

- [x] 2. 实现 SchemaValidator
  - [x] 2.1 创建 crawler/schema_validator.py（检查并补全 content_items 表字段）

- [x] 3. 实现 DetailFetcher
  - [x] 3.1 创建 crawler/detail_fetcher.py（HTTP请求+HTML解析，FetchResult数据结构）

- [x] 4. 实现 DataWriter
  - [x] 4.1 创建 crawler/data_writer.py（psycopg3 upsert，JSONB合并策略）

- [ ] 5. 实现 Scheduler 和入口脚本
  - [x] 5.1 创建 crawler/scheduler.py（schedule库定时调度，任务锁）
  - [x] 5.2 创建 crawler/run_crawler.py（CLI参数解析，任务编排）

- [x] 6. 验证和测试
  - [x] 6.1 验证 Python 语法正确性
  - [x] 6.2 测试 --limit 10 小批量爬取
