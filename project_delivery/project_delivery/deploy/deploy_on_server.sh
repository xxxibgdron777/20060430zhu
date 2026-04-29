#!/bin/bash
# ============================================================
# 财务综述 Agent · 腾讯云轻量应用服务器一键部署脚本
# 适用服务器: 43.156.129.176 (Singapore, lhins-lxew0hbj)
# 使用方式: 上传到服务器后执行 bash deploy_on_server.sh
# ============================================================

set -e

echo "=========================================="
echo "  财务综述 Agent · 服务器部署脚本"
echo "  服务器: 43.156.129.176"
echo "=========================================="

APP_DIR="/app/financial-agent"
echo "[INFO] 创建应用目录..."
mkdir -p $APP_DIR

echo "[INFO] 复制项目文件到服务器..."
# 请在本机执行以下命令上传文件（需要先安装 scp）：
# scp -r ./backend ./frontend ./管理报表.xlsx ./deploy root@43.156.129.176:$APP_DIR/

echo ""
echo "=========================================="
echo "  请在本机执行以下命令上传文件："
echo "=========================================="
echo ""
echo "  scp -r backend frontend 管理报表.xlsx deploy root@43.156.129.176:$APP_DIR/"
echo ""
echo "  上传完成后，继续执行以下命令："
echo ""
echo "  ssh root@43.156.129.176"
echo "  cd $APP_DIR"
echo "  bash deploy/deploy.sh"
echo ""
echo "=========================================="
