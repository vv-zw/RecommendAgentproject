# 部署计划：AI 影视推荐系统上线

## 任务重述

将本地运行的 AI 影视推荐系统部署上线，让其他人可以通过公网访问。提供两种方案供选择：**内网穿透**（零成本、快速演示）和**云服务器部署**（稳定可靠、适合长期运行）。

## 当前状态分析

- **后端**：Flask API 服务（`api/app.py`），端口 5001，依赖 PostgreSQL + DeepSeek API
- **前端**：React 18 + Vite，开发端口 3000，构建后为静态文件
- **数据库**：PostgreSQL，本地 127.0.0.1:5432
- **AI**：DeepSeek API（通过环境变量 `DEEPSEEK_API_KEY` 配置）
- **无 Docker 文件**：项目根目录没有 Dockerfile 或 docker-compose.yml
- **前端代理**：Vite 开发模式代理 `/api` 到 `localhost:5001`

## 方案对比

| 维度 | 内网穿透（ngrok） | 云服务器部署 |
|------|-------------------|-------------|
| **成本** | 免费（有带宽限制） | 约 30-60 元/月（轻量服务器） |
| **稳定性** | 依赖本机一直开着 | 7×24 小时稳定运行 |
| **速度** | 一般（经过中转服务器） | 快（直连） |
| **域名** | 随机子域名（如 xxx.ngrok.io） | 可绑定自己的域名 |
| **适合场景** | 演示、面试展示、临时分享 | 正式上线、长期运行 |
| **部署难度** | ⭐ 极简（5 分钟） | ⭐⭐⭐ 中等（1-2 小时） |

---

## 方案 A：内网穿透（ngrok）— 快速演示

### 步骤 1：安装 ngrok

从 https://ngrok.com/download 下载 Windows 版，解压到任意目录。

### 步骤 2：启动后端服务

```bash
cd d:\RecommendAgentProject
python api/app.py
```

确认服务在 `http://localhost:5001` 正常运行。

### 步骤 3：启动前端开发服务器

```bash
cd d:\RecommendAgentProject\frontend
npm run dev
```

确认前端在 `http://localhost:3000` 正常运行。

### 步骤 4：启动 ngrok 穿透

```bash
ngrok http 3000
```

ngrok 会分配一个公网 URL（如 `https://xxxx.ngrok-free.app`），其他人访问这个 URL 即可使用。

### 注意事项

- 本机必须一直开着，关机则服务停止
- ngrok 免费版有连接数限制
- 前端开发服务器的 Vite 代理会自动将 `/api` 请求转发到本地后端

---

## 方案 B：云服务器部署 — 正式上线

### 步骤 1：购买云服务器

推荐配置：
- **阿里云轻量应用服务器** 或 **腾讯云轻量应用服务器**
- 系统：Ubuntu 22.04 LTS
- 配置：2 核 2G（约 30-50 元/月）
- 系统盘：40GB SSD
- 带宽：1-3Mbps

### 步骤 2：服务器环境初始化

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip -y

# 安装 PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# 安装 Nginx
sudo apt install nginx -y

# 安装 Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# 安装 Git
sudo apt install git -y
```

### 步骤 3：配置 PostgreSQL

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 创建数据库和用户
CREATE USER movie_rec WITH PASSWORD '你的强密码';
CREATE DATABASE movie_recommendation OWNER movie_rec;
GRANT ALL PRIVILEGES ON DATABASE movie_recommendation TO movie_rec;

# 退出
\q
```

### 步骤 4：上传项目代码

```bash
# 在服务器上
git clone <你的仓库地址> /opt/recommend-project
cd /opt/recommend-project

# 或者用 scp 从本地上传
# scp -r d:\RecommendAgentProject\ root@你的服务器IP:/opt/recommend-project/
```

### 步骤 5：配置后端环境

```bash
cd /opt/recommend-project

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn

# 配置环境变量
cp .env.example .env
# 编辑 .env，修改以下内容：
# PGHOST=127.0.0.1
# PGPORT=5432
# PGDATABASE=movie_recommendation
# PGUSER=movie_rec
# PGPASSWORD=你的强密码
# PGSCHEMA=app
# DEEPSEEK_API_KEY=你的API密钥
# SECRET_KEY=随机生成的强密钥
```

### 步骤 6：初始化数据库

```bash
source venv/bin/activate
python scripts/init_db.py
python scripts/import_content_items.py  # 如果有初始数据
```

### 步骤 7：构建前端

```bash
cd /opt/recommend-project/frontend
npm install
npm run build
# 构建产物在 frontend/dist/ 目录
```

### 步骤 8：配置 Nginx

创建 `/etc/nginx/sites-available/recommend-app`：

```nginx
server {
    listen 80;
    server_name 你的域名或IP;

    # 前端静态文件
    location / {
        root /opt/recommend-project/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/recommend-app /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # 删除默认配置
sudo nginx -t  # 测试配置
sudo systemctl restart nginx
```

### 步骤 9：配置 systemd 服务

创建 `/etc/systemd/system/recommend-api.service`：

```ini
[Unit]
Description=AI Movie Recommendation API
After=network.target postgresql.service

[Service]
User=root
WorkingDirectory=/opt/recommend-project
Environment="PATH=/opt/recommend-project/venv/bin"
EnvironmentFile=/opt/recommend-project/.env
ExecStart=/opt/recommend-project/venv/bin/gunicorn -w 4 -b 127.0.0.1:5001 api.app:create_app()
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable recommend-api
sudo systemctl start recommend-api
sudo systemctl status recommend-api  # 检查状态
```

### 步骤 10：配置防火墙

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

同时在云服务器控制台的**安全组**中开放 80 和 443 端口。

### 步骤 11：（可选）配置 HTTPS

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d 你的域名
```

---

## 假设与决策

1. **推荐方案 B**：如果是面试展示或正式上线，云服务器部署更专业、更稳定
2. **数据库**：使用服务器本地 PostgreSQL，不需要额外购买云数据库
3. **前端**：构建为静态文件由 Nginx 直接托管，不需要单独的 Node.js 服务
4. **后端**：使用 Gunicorn 作为 WSGI 服务器，4 个 worker 进程
5. **不需要 Docker**：直接部署更简单，适合单台服务器
6. **旧版服务（端口 5000）**：不需要部署，只部署新版 Agent API（端口 5001）

## 验证步骤

1. 访问 `http://服务器IP` 能看到前端页面
2. 注册/登录功能正常
3. AI 对话功能正常（能调用 DeepSeek API）
4. 推荐结果正常返回
5. SSE 流式输出正常
