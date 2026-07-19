FROM python:3.11-slim

WORKDIR /app

# 安装依赖（使用清华镜像加速）
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
# 安装中文字体（报告图表需要，阿里云镜像直连避免 apt 源不可达）
RUN curl -sL --max-time 30 -o /tmp/wqy.deb 'http://mirrors.aliyun.com/debian/pool/main/f/fonts-wqy-microhei/fonts-wqy-microhei_0.2.0-beta-3.1_all.deb' && dpkg -i /tmp/wqy.deb && rm /tmp/wqy.deb && fc-cache -fv

# 复制代码（不包含 pycache 和 xlsx.old 文件）
COPY backend/main.py .
COPY backend/_gen_report_sanlitun.py .
COPY backend/_gen_report_sanlitun_full.py .
COPY backend/_gen_yz.py .
COPY backend/_gen_report_orig.py .
COPY backend/data_loader.py .
COPY backend/calculators.py .
COPY backend/agent.py .
COPY backend/api_extensions.py .
COPY backend/special_logic.py .
COPY backend/admin_api.py .
COPY backend/silver_headlines.py .
COPY backend/silver_headlines_data.json .
COPY backend/policy_data.json .
COPY backend/rating_system.py .
COPY backend/industry_benchmark.py .
COPY backend/ratings.py .
COPY backend/team_tips.json .
COPY backend/analysis_agent.py .
COPY backend/monthly_beijing_report.py .
COPY backend/ai_router.py .
COPY backend/briefing_api.py .
COPY backend/briefing_cache.py .
COPY backend/briefing_rules.py .
COPY backend/vip_progress.py .
COPY backend/feishu_sync.py .
COPY backend/feishu_config.py .
COPY backend/rag_service.py .
COPY backend/qwen_client.py .
COPY backend/team_report.py .
COPY backend/销售排名.py .

# 复制数据文件
COPY 管理报表.xlsx .

# 暴露端口
EXPOSE 80

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
