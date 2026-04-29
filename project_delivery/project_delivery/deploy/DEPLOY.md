# 财务综述 Agent · 部署指南

## 服务器信息
- **IP**: 43.156.129.176
- **地域**: 新加坡 (ap-singapore)
- **系统**: OpenCloudOS (Linux)
- **实例ID**: lhins-lxew0hbj

---

## 部署方式一：手动上传 + 一键部署（推荐）

### 第一步：在本机执行文件上传

```bash
# 上传项目文件（需要先安装 scp 或使用 PowerShell）
scp -r backend frontend "管理报表.xlsx" deploy root@43.156.129.176:/app/financial-agent/
```

> Windows PowerShell 示例：
> ```powershell
> scp -r .\backend .\frontend ".\管理报表.xlsx" .\deploy root@43.156.129.176:/app/financial-agent/
> ```

### 第二步：在服务器执行部署脚本

```bash
# SSH 登录服务器
ssh root@43.156.129.176

# 进入项目目录
cd /app/financial-agent

# 执行一键部署
bash deploy/deploy.sh
```

---

## 部署方式二：手动逐步部署

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 2. 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 3. 上传文件后进入目录
cd /app/financial-agent

# 4. 开放防火墙端口
firewall-cmd --permanent --add-port=80/tcp   # HTTP（前端）
firewall-cmd --permanent --add-port=8000/tcp # API（后端）
firewall-cmd --reload

# 5. 构建并启动
docker-compose -f deploy/docker-compose.yml build --no-cache
docker-compose -f deploy/docker-compose.yml up -d

# 6. 验证
curl http://localhost:8000/health
```

---

## 部署后访问

- **前端地址**: http://43.156.129.176
- **API地址**: http://43.156.129.176:8000/health（管理后台API）

---

## 常用维护命令

```bash
# 查看日志
docker-compose -f /app/financial-agent/deploy/docker-compose.yml logs -f

# 重启服务
docker-compose -f /app/financial-agent/deploy/docker-compose.yml restart

# 更新代码后重新部署
docker-compose -f /app/financial-agent/deploy/docker-compose.yml up -d --build

# 停止服务
docker-compose -f /app/financial-agent/deploy/docker-compose.yml down
```

---

## 项目结构说明

```
financial-agent/
├── backend/          # FastAPI 后端
│   ├── main.py          # 主程序（API 端点）
│   ├── calculators.py   # 核心计算函数
│   ├── data_loader.py  # Excel 数据加载
│   ├── agent.py        # AI Agent 逻辑
│   ├── api_extensions.py# API 扩展
│   ├── vip_progress.py # VIP 疗程管理
│   └── Dockerfile      # Docker 镜像构建
├── frontend/         # Vue 前端
│   └── index.html       # 单页应用
├── deploy/           # 部署配置
│   ├── docker-compose.yml  # 容器编排
│   ├── nginx.conf        # Nginx 反向代理
│   └── deploy.sh         # 一键部署脚本
└── 管理报表.xlsx     # 财务数据源（需上传）
```

---

## TAT Agent 安装（启用自动化）

如需启用 CodeBuddy 远程执行功能，请在腾讯云控制台安装 TAT：

1. 进入 [自动化助手 TAT](https://console.cloud.tencent.com/tat)
2. 选择「新加坡」地域
3. 点击「安装 Agent」→ 选择实例 `lhins-lxew0hbj`
4. 安装完成后即可使用 CodeBuddy 远程部署功能
