"""团队专项报告路由（占位模块）
TODO: 实现国管局、三里屯等团队的专项报告生成
"""
from fastapi import APIRouter

router = APIRouter(tags=["team_report"])

# 此模块暂未实现，相关报告功能请使用：
# - /api/team/report/sanlitun (三里屯诊所透视表)
# - 国管局报告请参考前端直接加载的静态HTML文件
