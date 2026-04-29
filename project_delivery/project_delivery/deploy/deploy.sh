#!/bin/bash
# ============================================================
# 财务综述 Agent · 一键安装 + 部署脚本
# 在服务器 43.156.129.176 上以 root 身份运行
# ============================================================

set -e

echo "=========================================="
echo "  财务综述 Agent · 部署脚本"
echo "  $(date)"
echo "=========================================="

# 1. 安装 TAT Agent（如尚未安装）
if ! command -v /usr/local/qcloud/tat_agent/tat_agent &> /dev/null; then
    echo "[STEP 1] 安装 TAT Agent..."
    wget -qO - https://tat-1258344699.cos-internal.accelerate.tencentcos.cn/tat_agent/tat_agent_installer.sh | sh
    sleep 3
    if /usr/local/qcloud/tat_agent/tat_agent &>/dev/null & sleep 1; then
        echo "[OK] TAT Agent 已安装并启动"
    else
        echo "[WARN] TAT Agent 安装可能有问题，继续..."
    fi
else
    echo "[SKIP] TAT Agent 已安装"
fi

# 2. 检查并安装 Docker
if ! command -v docker &> /dev/null; then
    echo "[STEP 2] 安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "[OK] Docker 已安装"
else
    echo "[SKIP] Docker 已安装"
fi

# 3. 检查 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "[STEP 3] 安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "[OK] Docker Compose 已安装"
else
    echo "[SKIP] Docker Compose 已安装"
fi

# 4. 检查管理报表.xlsx
if [ ! -f "./管理报表.xlsx" ]; then
    echo "[ERROR] 管理报表.xlsx 未找到，请上传后再试！"
    exit 1
else
    echo "[OK] 管理报表.xlsx 已就绪"
fi

# 5. 开放防火墙端口
echo "[STEP 5] 开放防火墙端口 80..."
# Ubuntu/Debian (ufw)
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp 2>/dev/null || true
fi
# CentOS/RHEL (firewalld)
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
fi
echo "[OK] 防火墙端口已开放"

# 6. 构建并启动容器
echo "[STEP 6] 构建并启动容器..."
cd /app/financial-agent

# 停止旧容器
docker-compose down 2>/dev/null || true

# 构建镜像（包含前端+后端）
docker-compose build --no-cache

# 启动服务
docker-compose up -d

# 7. 等待并验证
echo "[STEP 7] 验证服务状态..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:80/health > /dev/null 2>&1; then
        echo "[OK] 后端 API 已就绪！"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "[ERROR] 后端启动超时，查看日志："
        docker-compose logs backend | tail -20
        exit 1
    fi
    sleep 2
done

# 8. 获取服务器IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s api.ipify.org 2>/dev/null || echo "43.156.129.176")

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  前端访问: http://$SERVER_IP"
echo "  API健康:  http://$SERVER_IP/health"
echo ""
echo "  常用维护命令："
echo "    查看日志:   cd /app/financial-agent && docker-compose logs -f"
echo "    停止服务:   cd /app/financial-agent && docker-compose down"
echo "    重启服务:   cd /app/financial-agent && docker-compose restart"
echo "    更新部署:   cd /app/financial-agent && docker-compose pull && docker-compose up -d"
echo ""
echo "  注意事项："
echo "    1. 管理报表.xlsx 挂载为只读，如需更新请替换后重启"
echo "    2. VIP数据存储在 ./deploy/vip_data/"
echo "=========================================="
