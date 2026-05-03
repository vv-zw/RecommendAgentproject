# 实现任务列表：用户偏好驱动页面

## 任务

- [x] 1. 确认并创建 user_preferences 表迁移
  - [x] 1.1 检查 002_user_preferences.sql 迁移文件是否存在且字段正确
  - [x] 1.2 若字段不完整则补充迁移文件

- [x] 2. 后端工具函数与新增 API 接口（api/routes.py）
  - [x] 2.1 新增 build_preference_match_sql 工具函数
  - [x] 2.2 新增 build_preference_context 工具函数
  - [x] 2.3 新增 GET /api/users/{user_id}/preferences 接口
  - [x] 2.4 新增 GET /api/users/{user_id}/movies/preference 接口
  - [x] 2.5 新增 GET /api/users/{user_id}/series/preference 接口
  - [x] 2.6 修改 POST /api/agent/chat 注入偏好上下文

- [x] 3. 扩展 AgentManager 支持偏好上下文
  - [x] 3.1 修改 AgentManager.process_user_request 签名接受 preference_context
  - [x] 3.2 修改 ToolOrchestrator.execute_tools 使用偏好上下文加权推荐
  - [x] 3.3 修改 ResponseGenerator.generate_response 生成个性化回复

- [x] 4. 前端 API 层扩展（frontend/src/api/content.ts）
  - [x] 4.1 新增 UserPreference、UserPreferencesResponse、PreferenceMediaListResponse 类型
  - [x] 4.2 新增 getPreferenceMovies、getPreferenceSeries、getUserPreferences 方法

- [x] 5. 前端页面改造
  - [x] 5.1 改造 Movies.tsx：登录态调用偏好接口，展示 isFallback 提示横幅
  - [x] 5.2 改造 Series.tsx：登录态调用偏好接口，展示 isFallback 提示横幅
  - [x] 5.3 重构 Watchlist.tsx：替换模拟数据为真实 API，支持乐观更新移除
  - [x] 5.4 改造 AgentAssistant.tsx：动态生成快捷词条，失败时降级为默认词条
