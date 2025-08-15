"""
内容审核统计分析系统 FastAPI 应用
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime, timedelta
import logging
import time
from contextlib import asynccontextmanager

# 导入现有模块
from config import setup_logging, validate_date_range
from database import DatabaseManager, create_db_manager
from analyzer import AuditStatsAnalyzer

# 设置日志
logger = setup_logging()

# 全局组件实例
db_manager = None
analyzer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global db_manager, analyzer
    
    logger.info("初始化审核统计分析系统...")
    
    try:
        # 初始化组件
        db_manager = create_db_manager()
        analyzer = AuditStatsAnalyzer(db_manager)
        
        logger.info("系统初始化完成")
        yield
        
    except Exception as e:
        logger.error(f"系统初始化失败: {e}")
        raise
    finally:
        if db_manager:
            db_manager.close()
        logger.info("系统已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="内容审核统计分析系统",
    description="提供URL、图片、多媒体内容审核的统计分析接口",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============== 响应模型 ===============

class APIResponse(BaseModel):
    """统一API响应模型"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    execution_time: Optional[float] = None

# =============== 辅助函数 ===============

def create_api_response(success: bool, data: Any = None, error: str = None, execution_time: float = None) -> APIResponse:
    """创建API响应"""
    return APIResponse(
        success=success,
        data=data,
        error=error,
        execution_time=execution_time
    )

def validate_components():
    """验证组件是否初始化"""
    if not all([db_manager, analyzer]):
        raise HTTPException(status_code=503, detail="系统组件未完全初始化")

def validate_date_params(start_date: Optional[str], end_date: Optional[str]) -> tuple:
    """验证日期参数"""
    if start_date and end_date:
        if not validate_date_range(start_date, end_date):
            raise HTTPException(status_code=400, detail="日期范围无效或超出限制")
    return start_date, end_date

# =============== 基础接口 ===============

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "内容审核统计分析系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", response_model=APIResponse)
async def get_system_health():
    """系统健康检查"""
    start_time = time.time()
    
    try:
        validate_components()
        
        # 检查数据库连接
        db_healthy = db_manager.check_connection()
        
        # 获取今日统计
        today = datetime.now().date()
        today_str = today.strftime('%Y-%m-%d')
        tomorrow_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        
        today_overview = analyzer.get_overview_stats(today_str, tomorrow_str)
        
        # 计算系统指标
        health_data = {
            'database_status': 'healthy' if db_healthy else 'unhealthy',
            'api_status': 'healthy',
            'last_check': datetime.now().isoformat(),
            'today_stats': today_overview
        }
        
        execution_time = time.time() - start_time
        
        return create_api_response(
            success=True,
            data=health_data,
            execution_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"系统健康检查失败: {e}")
        return create_api_response(
            success=False,
            error=str(e),
            execution_time=execution_time
        )

# =============== 1. 整体概览统计 ===============

@app.get("/stats/overview", response_model=APIResponse)
async def get_overview_stats(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """整体概览统计"""
    start_time = time.time()
    
    try:
        validate_components()
        logger.info(f"API请求: 获取整体概览统计，时间范围: {start_date} - {end_date}")
        
        # 验证日期范围
        start_date, end_date = validate_date_params(start_date, end_date)
        
        # 执行统计分析
        result = analyzer.get_overview_stats(start_date, end_date)
        
        execution_time = time.time() - start_time
        logger.info(f"整体概览统计完成，耗时: {execution_time:.2f}秒")
        
        return create_api_response(
            success=True,
            data=result,
            execution_time=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"整体概览统计失败: {e}，耗时: {execution_time:.2f}秒")
        return create_api_response(
            success=False,
            error=str(e),
            execution_time=execution_time
        )

# =============== 2. URL审核统计 ===============

@app.get("/stats/url-audit", response_model=APIResponse)
async def get_url_audit_stats(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """URL审核统计"""
    start_time = time.time()
    
    try:
        validate_components()
        logger.info(f"API请求: 获取URL审核统计，时间范围: {start_date} - {end_date}")
        
        start_date, end_date = validate_date_params(start_date, end_date)
        
        result = analyzer.get_url_audit_stats(start_date, end_date)
        
        execution_time = time.time() - start_time
        logger.info(f"URL审核统计完成，耗时: {execution_time:.2f}秒")
        
        return create_api_response(
            success=True,
            data=result,
            execution_time=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"URL审核统计失败: {e}，耗时: {execution_time:.2f}秒")
        return create_api_response(
            success=False,
            error=str(e),
            execution_time=execution_time
        )

# =============== 3. 图片审核统计 ===============

@app.get("/stats/image-audit", response_model=APIResponse)
async def get_image_audit_stats(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """图片审核统计"""
    start_time = time.time()
    
    try:
        validate_components()
        logger.info(f"API请求: 获取图片审核统计，时间范围: {start_date} - {end_date}")
        
        start_date, end_date = validate_date_params(start_date, end_date)
        
        result = analyzer.get_image_audit_stats(start_date, end_date)
        
        execution_time = time.time() - start_time
        logger.info(f"图片审核统计完成，耗时: {execution_time:.2f}秒")
        
        return create_api_response(
            success=True,
            data=result,
            execution_time=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"图片审核统计失败: {e}，耗时: {execution_time:.2f}秒")
        return create_api_response(
            success=False,
            error=str(e),
            execution_time=execution_time
        )

# =============== 4. 多媒体审核统计 ===============

@app.get("/stats/multimedia-audit", response_model=APIResponse)
async def get_multimedia_audit_stats(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """多媒体审核统计"""
    start_time = time.time()
    
    try:
        validate_components()
        logger.info(f"API请求: 获取多媒体审核统计，时间范围: {start_date} - {end_date}")
        
        start_date, end_date = validate_date_params(start_date, end_date)
        
        result = analyzer.get_multimedia_audit_stats(start_date, end_date)
        
        execution_time = time.time() - start_time
        logger.info(f"多媒体审核统计完成，耗时: {execution_time:.2f}秒")
        
        return create_api_response(
            success=True,
            data=result,
            execution_time=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"多媒体审核统计失败: {e}，耗时: {execution_time:.2f}秒")
        return create_api_response(
            success=False,
            error=str(e),
            execution_time=execution_time
        )

# =============== 启动配置 ===============

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("内容审核统计分析系统 FastAPI 服务")
    print("=" * 60)
    print("🚀 启动地址: http://localhost:8000")
    print("📖 API文档: http://localhost:8000/docs")
    print("🏥 健康检查: http://localhost:8000/health")
    print("📊 统计功能:")
    print("   - 整体概览: /stats/overview")
    print("   - URL审核: /stats/url-audit")
    print("   - 图片审核: /stats/image-audit")
    print("   - 多媒体审核: /stats/multimedia-audit")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )