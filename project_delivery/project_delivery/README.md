# 财务综述 Agent

基于 Excel 数据源的智能财务分析 Web 应用，支持产品线/创业团队下钻分析、预算对比、AI 智能问答等功能。

## 📋 功能概览

### 三大核心模块

1. **经营分析** - 产品线/创业团队的核心财务数据展示
   - KPI 卡片：总收入、总支出、总结余、结余率（含同比/环比）
   - 环形图：板块结余占比
   - 趋势图：全年月度收入趋势
   - 三级下钻：板块 → 产品 → 项目 / 团队 → 上级 → 核算单元
   - 特殊团队逻辑：物业管理、01.老干局、健康管理

2. **智能问答** - 自然语言财务查询
   - 支持关键词查询：结余率、收入、支出、管理费占比
   - 智能下钻：点击结果中的名称继续深挖
   - AI 分析建议：自动检测异常数据

3. **预算对比** - 实际 vs 预算达成分析
   - Excel 上传：支持标准预算模板
   - 双向编辑：前端直接修改预算值
   - 离线缓存：修改自动保存到本地
   - 导出 Excel：下载对比结果

## 🏗️ 技术栈

- **后端**: Python FastAPI
- **前端**: HTML5 + CSS3 + Vanilla JavaScript
- **图表**: ECharts 5.5
- **数据源**: Excel (.xlsx)
- **部署**: 腾讯云 CloudBase / 任意 Linux 服务器

## 📁 项目结构

```
financial-agent/
├── backend/
│   ├── main.py              # FastAPI 主程序
│   ├── data_loader.py       # 数据加载模块
│   ├── calculators.py        # 核心计算模块
│   ├── special_logic.py      # 特殊逻辑模块
│   ├── agent.py             # AI Agent 模块
│   ├── api_extensions.py     # API 扩展模块
│   ├── requirements.txt      # Python 依赖
│   └── 管理报表.xlsx          # 数据源文件
├── frontend/
│   └── index.html           # 前端单页应用
├── README.md                 # 项目文档
└── _restart.py              # 服务重启脚本
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 准备数据

将你的 `管理报表.xlsx` 文件放入 `backend/` 目录。

**Excel 文件要求**:
- Sheet1: `产品` - 包含年、月、业务板块、产品、项目、收入、支出、平台管理费、损益列
- Sheet2: `创业团队` - 包含年、月、H团队线性质、H团队线-上级、H团队线-核算、收支、资金流向、金额g列

### 3. 启动服务

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问应用

打开浏览器访问: `http://localhost:8000`

## 📊 数据计算规则

### 金额格式
- 单位：万元
- 取整：四舍五入到整数
- 千分位：使用 `toLocaleString()`

### 百分比格式
- 整数带符号：`+5%`, `-12%`
- null 显示为 `-`

### 核心公式
```
结余 = 收入 - 支出 - 平台管理费
同比% = (当期 - 去年同期) / |去年同期| × 100%
环比% = (当期 - 上月) / |上月| × 100%
```

### 支持团队特殊规则
```
支持团队结余 = 0 - 支持团队自身支出 - (其他板块管理费合计 × -1)
```

## 🔌 API 接口

### 基础接口
- `GET /health` - 服务健康检查
- `GET /api/meta` - 获取数据元信息
- `GET /api/kpi` - 获取 KPI 数据
- `GET /api/trend` - 获取月度趋势
- `GET /api/pie` - 获取饼图数据

### 下钻接口
- `POST /api/product/drill` - 产品线下钻
- `POST /api/team/drill` - 团队线下钻

### 智能问答
- `POST /api/ai/query` - AI 问答查询
- `GET /api/ai/suggestions` - AI 分析建议

### 特殊接口
- `GET /api/property/comparison` - 物业管理对比（收付实现 vs 权责发生）
- `GET /api/laoganju/distribution` - 老干局分布
- `GET /api/team/share` - 团队经营分享

### 预算接口
- `POST /api/budget/upload` - 上传预算文件
- `GET /api/budget/compare` - 获取对比数据
- `POST /api/budget/update` - 更新预算数据
- `GET /api/budget/export` - 导出对比结果

## 🎨 前端使用

### 月份筛选
- 单选：1月 ~ 12月
- 累计：本年1月至当前月
- 3-12月：本年3月至当前月

### 模式切换
- **产品线模式**：板块 → 产品 → 项目
- **创业团队模式**：团队性质 → 上级 → 核算单元

### 快捷操作
- 点击卡片行：下钻到下一级
- 返回按钮：返回上一级
- 排序按钮：按结余/收入/支出排序

### 智能问答预设问题
- 哪些板块结余率低于5%？
- 支出增长最快的产品？
- 物业板块详情
- 管理费占比超过10%的板块？

## 🚀 部署指南

### 腾讯云 CloudBase 部署

1. **安装 CloudBase CLI**
```bash
npm install -g @cloudbase/cli
```

2. **登录腾讯云**
```bash
tcb login
```

3. **初始化项目**
```bash
cd financial-agent/backend
tcb init
```

4. **部署后端**
```bash
tcb deploy
```

### 传统服务器部署

1. **安装 Python 3.8+**
```bash
# Ubuntu
sudo apt update
sudo apt install python3.9 python3-pip

# CentOS
sudo yum install python39 python39-pip
```

2. **安装依赖**
```bash
cd backend
pip3 install -r requirements.txt
```

3. **配置 Nginx**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. **使用 Systemd 管理服务**
```bash
sudo nano /etc/systemd/system/financial-agent.service
```

内容：
```ini
[Unit]
Description=Financial Agent
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/financial-agent/backend
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable financial-agent
sudo systemctl start financial-agent
```

## 🔧 配置说明

### 数据源位置
默认数据源路径：`backend/管理报表.xlsx`

修改 `data_loader.py` 中的 `EXCEL_PATH` 可更改路径。

### 缓存时间
默认缓存 10 分钟（600秒），修改 `main.py` 中的 `CACHE_SECONDS`。

### 管理员密码
默认密码：`admin`

修改 `main.py` 中的 `_budget_admin_token`。

## 📝 开发指南

### 添加新的计算逻辑

1. 在 `calculators.py` 中添加函数
2. 在 `main.py` 中添加 API 端点
3. 在前端 `index.html` 中调用接口

### 添加新的查询模式

在 `agent.py` 的 `query()` 方法中添加正则匹配逻辑。

### 自定义颜色主题

修改 `index.html` 中的 CSS 变量：
```css
:root {
  --accent: #F6B43E;  /* 主色调 */
  --green: #2C9A6E;   /* 正值/增长 */
  --red: #E35F5F;     /* 负值/下降 */
}
```

## ❓ 常见问题

**Q: 数据未加载？**
A: 检查 `管理报表.xlsx` 是否存在且格式正确。

**Q: 图表不显示？**
A: 检查浏览器控制台是否有跨域错误，确保 API 地址正确。

**Q: 下钻无数据？**
A: 检查选中的月份是否有数据，确认年份和月份字段格式。

## 📄 License

MIT License

## 🤝 Contributing

欢迎提交 Issue 和 Pull Request！

## 📞 联系方式

如有问题，请联系开发者。
