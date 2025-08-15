
"""
内容审核统计分析系统 FastAPI 应用
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime, timedelta
import os
import logging
import time
from contextlib import asynccontextmanager

# 导入现有模块
from config import setup_logging, validate_date_range
from database import DatabaseManager, create_db_manager
from analyzer import AuditStatsAnalyzer
from visualization import DataVisualizer
from exporter import ReportExporter
from models import ExportRequest

# 设置日志
logger = setup_logging()

# 全局组件实例
db_manager = None
analyzer = None
visualizer = None
exporter = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global db_manager, analyzer, visualizer, exporter
    
    logger.info("初始化审核统计分析系统...")
    
    try:
        # 初始化组件（直接使用 api.py 中的逻辑）
        db_manager = create_db_manager()
        analyzer = AuditStatsAnalyzer(db_manager)
        visualizer = DataVisualizer()
        exporter = ReportExporter()
        
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

class ExportRequestModel(BaseModel):
    """导出请求模型"""
    format: str = Field(..., description="导出格式: excel/csv/pdf")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    include_charts: bool = Field(True, description="是否包含图表")
    include_details: bool = Field(True, description="是否包含详细信息")

# =============== 辅助函数 ===============

def create_api_response(success: bool, data: Any = None, error: str = None, execution_time: float = None) -> APIResponse:
    """创建API响应（复用 api.py 中的逻辑）"""
    return APIResponse(
        success=success,
        data=data,
        error=error,
        execution_time=execution_time
    )

def validate_components():
    """验证组件是否初始化"""
    if not all([db_manager, analyzer, visualizer, exporter]):
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
    """系统健康检查（直接转换 api.py 中的 get_system_health）"""
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
    """整体概览统计（直接转换 api.py 中的 get_overview_stats）"""
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
    """URL审核统计（直接转换 api.py 中的 get_url_audit_stats）"""
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
    """图片审核统计（直接转换 api.py 中的 get_image_audit_stats）"""
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
    """多媒体审核统计（直接转换 api.py 中的 get_multimedia_audit_stats）"""
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

# =============== 数据可视化 ===============

@app.get("/stats/visualizations", response_model=APIResponse)
async def generate_visualizations(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """生成数据可视化（直接转换 api.py 中的 generate_visualizations）"""
    start_time = time.time()
    
    try:
        validate_components()
        logger.info(f"API请求: 生成数据可视化图表，时间范围: {start_date} - {end_date}")
        
        # 获取统计数据
        overview_data = analyzer.get_overview_stats(start_date, end_date)
        url_data = analyzer.get_url_audit_stats(start_date, end_date)
        image_data = analyzer.get_image_audit_stats(start_date, end_date)
        multimedia_data = analyzer.get_multimedia_audit_stats(start_date, end_date)
        
        # 构建统计数据
        stats_data = {
            'overview': overview_data,
            'url_audit': url_data,
            'image_audit': image_data,
            'multimedia_audit': multimedia_data
        }
        
        # 生成可视化图表
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        chart_files = visualizer.generate_all_visualizations(stats_data, f"{timestamp}_")
        
        execution_time = time.time() - start_time
        logger.info(f"数据可视化图表生成完成，共生成 {len(chart_files)} 个文件，耗时: {execution_time:.2f}秒")
        
        return create_api_response(
            success=True,
            data={
                'chart_files': chart_files,
                'chart_count': len(chart_files),
                'generation_time': execution_time
            },
            execution_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"生成数据可视化图表失败: {e}，耗时: {execution_time:.2f}秒")
        return create_api_response(
            success=False,
            error=str(e),
            execution_time=execution_time
        )

# =============== 报告导出 ===============

@app.post("/export/report", response_model=APIResponse)
async def export_report(request: ExportRequestModel):
    """导出报告（直接转换 api.py 中的 export_report）"""
    start_time = time.time()
    
    try:
        validate_components()
        logger.info(f"API请求: 导出报告，格式: {request.format}，时间范围: {request.start_date} - {request.end_date}")
        
        # 验证格式
        if request.format not in ['excel', 'csv', 'pdf']:
            raise HTTPException(status_code=400, detail=f"不支持的导出格式: {request.format}")
        
        # 验证日期范围
        start_date, end_date = validate_date_params(request.start_date, request.end_date)
        
        # 获取统计数据
        overview_data = analyzer.get_overview_stats(start_date, end_date)
        url_data = analyzer.get_url_audit_stats(start_date, end_date)
        image_data = analyzer.get_image_audit_stats(start_date, end_date)
        multimedia_data = analyzer.get_multimedia_audit_stats(start_date, end_date)
        
        stats_data = {
            'overview': overview_data,
            'url_audit': url_data,
            'image_audit': image_data,
            'multimedia_audit': multimedia_data
        }
        
        # 生成图表（如果需要）
        chart_files = []
        if request.include_charts and request.format.lower() == 'pdf':
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            chart_files = visualizer.generate_all_visualizations(stats_data, f"{timestamp}_")
        
        # 导出报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = request.filename if hasattr(request, 'filename') and request.filename else f"audit_report_{timestamp}"
        
        if request.format.lower() == 'excel':
            file_path = exporter.export_excel_report(stats_data, f"{filename}.xlsx")
        elif request.format.lower() == 'csv':
            file_path = exporter.export_csv_report(stats_data, f"{filename}.csv")
        elif request.format.lower() == 'pdf':
            file_path = exporter.export_pdf_report(stats_data, chart_files, f"{filename}.pdf")
        
        execution_time = time.time() - start_time
        logger.info(f"报告导出完成: {file_path}，耗时: {execution_time:.2f}秒")
        
        # 获取文件大小
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        return create_api_response(
            success=True,
            data={
                'file_path': file_path,
                'filename': os.path.basename(file_path),
                'file_format': request.format,
                'export_time': execution_time,
                'file_size': file_size,
                'download_url': f"/download/{os.path.basename(file_path)}"
            },
            execution_time=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"导出报告失败: {e}，耗时: {execution_time:.2f}秒")
        return create_api_response(
            success=False,
            error=str(e),
            execution_time=execution_time
        )

@app.get("/export/all-formats", response_model=APIResponse)
async def export_all_formats(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    include_charts: bool = Query(True, description="是否包含图表")
):
    """导出所有格式报告（直接转换 api.py 中的 export_all_formats）"""
    start_time = time.time()
    
    try:
        validate_components()
        logger.info(f"API请求: 导出所有格式报告，时间范围: {start_date} - {end_date}")
        
        start_date, end_date = validate_date_params(start_date, end_date)
        
        # 获取统计数据
        overview_data = analyzer.get_overview_stats(start_date, end_date)
        url_data = analyzer.get_url_audit_stats(start_date, end_date)
        image_data = analyzer.get_image_audit_stats(start_date, end_date)
        multimedia_data = analyzer.get_multimedia_audit_stats(start_date, end_date)
        
        stats_data = {
            'overview': overview_data,
            'url_audit': url_data,
            'image_audit': image_data,
            'multimedia_audit': multimedia_data
        }
        
        # 生成图表
        chart_files = []
        if include_charts:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            chart_files = visualizer.generate_all_visualizations(stats_data, f"{timestamp}_")
        
        # 导出所有格式
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        exported_files = exporter.export_all_formats(stats_data, chart_files, f"{timestamp}_")
        
        execution_time = time.time() - start_time
        logger.info(f"所有格式报告导出完成，共生成 {len(exported_files)} 个文件，耗时: {execution_time:.2f}秒")
        
        # 计算文件大小
        file_info = {}
        for format_type, file_path in exported_files.items():
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            file_info[format_type] = {
                'file_path': file_path,
                'filename': os.path.basename(file_path),
                'file_size': file_size,
                'download_url': f"/download/{os.path.basename(file_path)}"
            }
        
        return create_api_response(
            success=True,
            data={
                'exported_files': file_info,
                'chart_files': [os.path.basename(f) for f in chart_files],
                'total_files': len(exported_files) + len(chart_files),
                'export_time': execution_time
            },
            execution_time=execution_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"导出所有格式报告失败: {e}，耗时: {execution_time:.2f}秒")
        return create_api_response(
            success=False,
            error=str(e),
            execution_time=execution_time
        )

# =============== 文件下载 ===============

@app.get("/download/{filename}")
async def download_file(filename: str):
    """下载生成的文件"""
    # 查找文件
    possible_paths = [
        os.path.join("reports", filename),
        os.path.join("visualizations", filename)
    ]
    
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
    
    if not file_path:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 确定媒体类型
    if filename.endswith('.xlsx'):
        media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif filename.endswith('.csv'):
        media_type = 'text/csv'
    elif filename.endswith('.pdf'):
        media_type = 'application/pdf'
    elif filename.endswith('.png'):
        media_type = 'image/png'
    elif filename.endswith('.html'):
        media_type = 'text/html'
    else:
        media_type = 'application/octet-stream'
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
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
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )