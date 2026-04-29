#!/bin/bash
# ============================================================
# 财务综述 Agent · 一键部署脚本
# 适用于 Ubuntu/Debian Linux 服务器
# 用法: bash deploy/setup.sh
# ============================================================

set -e

echo "=========================================="
echo "  财务综述 Agent · 部署脚本"
echo "=========================================="

# 1. 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# 2. 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "[ERROR] docker-compose 未安装，正在安装..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 3. 检查管理报表.xlsx 是否存在
if [ ! -f "../管理报表.xlsx" ]; then
    echo "[ERROR] 管理报表.xlsx 未找到，请将其放置在项目根目录"
    exit 1
fi

echo "[OK] Docker & docker-compose 已就绪"

# 4. 停止旧容器（如有）
echo "[INFO] 停止旧容器..."
docker-compose down 2>/dev/null || true

# 5. 构建并启动
echo "[INFO] 构建并启动容器..."
docker-compose build --no-cache
docker-compose up -d

# 6. 等待后端启动
echo "[INFO] 等待后端服务就绪..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:80/health > /dev/null 2>&1; then
        echo "[OK] 后端服务已就绪！"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "[ERROR] 后端服务启动超时，请检查日志："
        docker-compose logs backend
        exit 1
    fi
    sleep 2
done

# 7. 显示访问信息
echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo "  前端访问地址: http://$(curl -s ifconfig.me 2>/dev/null || echo '服务器IP')"
echo "  API健康检查: http://$(curl -s ifconfig.me 2>/dev/null || echo '服务器IP')/health"
echo ""
echo "  常用命令："
echo "    查看日志:  docker-compose logs -f"
echo "    停止服务:  docker-compose down"
echo "    重启服务:  docker-compose restart"
echo "=========================================="
