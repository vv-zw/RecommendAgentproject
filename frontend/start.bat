@echo off
echo ========================================
echo   影视推荐AI助手 - 前端启动脚本
echo ========================================
echo.

echo 1. 安装依赖...
call npm install
if %errorlevel% neq 0 (
    echo 依赖安装失败！
    pause
    exit /b 1
)

echo.
echo 2. 启动开发服务器...
echo 前端将在 http://localhost:3000 启动
echo 请确保后端API在 http://localhost:5001 运行
echo.

call npm run dev