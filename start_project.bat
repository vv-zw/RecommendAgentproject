@echo off
echo ========================================
echo   影视推荐AI助手 - 完整项目启动脚本
echo ========================================
echo.

echo 注意：请确保已安装以下依赖：
echo 1. Python 3.8+
echo 2. Node.js 18+
echo 3. npm 9+
echo.

echo 步骤1：启动后端API服务器
echo 请在新终端中运行以下命令：
echo python api/app.py
echo.
echo 后端API将在 http://localhost:5001 启动
echo.

echo 步骤2：启动前端应用
echo 请在新终端中运行以下命令：
echo cd frontend
echo npm install
echo npm run dev
echo.
echo 前端将在 http://localhost:3000 启动
echo.

echo 步骤3：访问应用
echo 1. 打开浏览器访问 http://localhost:3000
echo 2. 注册新账户或使用测试账户登录
echo 3. 体验AI助手功能
echo.

echo 测试账户：
echo 用户名：testuser
echo 密码：test123
echo.

pause