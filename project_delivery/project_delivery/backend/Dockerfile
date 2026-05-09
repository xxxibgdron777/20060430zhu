FROM python:3.11-slim

WORKDIR /app

# 安装依赖（使用清华镜像加速）
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制代码（不包含 pycache 和 xlsx.old 文件）
COPY backend/main.py .
COPY backend/data_loader.py .
COPY backend/calculators.py .
COPY backend/agent.py .
COPY backend/api_extensions.py .
COPY backend/special_logic.py .
COPY backend/vip_progress.py .
COPY backend/admin_api.py .
COPY backend/silver_headlines.py .
COPY backend/rating_system.py .
COPY backend/industry_benchmark.py .
COPY backend/ratings.py .
COPY backend/team_tips.json .
COPY backend/analysis_agent.py .
COPY backend/monthly_beijing_report.py .

# 复制数据文件
COPY 管理报表.xlsx .

# 暴露端口
EXPOSE 80

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
