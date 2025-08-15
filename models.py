"""
数据模型定义
定义系统中使用的数据结构和模型类
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

class AuditStatus(Enum):
    """审核状态枚举"""
    COMPLIANT = "合规"
    NON_COMPLIANT = "不合规"
    UNCERTAIN = "不确定"
    FAILED = "审核失败"
    PENDING = "待审核"

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ViolationType(Enum):
    """违规类型枚举"""
    PORNOGRAPHY = "涉黄"
    POLITICS = "涉政"
    TERRORISM = "涉恐"
    ABUSE = "恶意辱骂"
    FRAUD = "虚假诈骗"
    ADVERTISEMENT = "广告推广"
    PROHIBITED = "违禁词"
    EXTREME_SENTIMENT = "舆情极端"
    BLACKLIST = "黑名单词"
    MAP_ISSUE = "地图问题"

@dataclass
class ViolationInfo:
    """违规信息数据类"""
    type: str
    description: str
    count: int = 0
    confidence: float = 0.0
    evidence: Optional[str] = None

@dataclass
class StatResult:
    """统计结果数据类"""
    total_count: int
    violation_count: int
    violation_rate: float
    breakdown: Dict[str, int]
    time_series: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if self.total_count > 0:
            self.violation_rate = self.violation_count / self.total_count
        else:
            self.violation_rate = 0.0

@dataclass
class UrlAuditRecord:
    """URL审核记录"""
    id: int
    url: str
    markdown: Optional[str]
    verdict: str
    reason: Optional[str]
    parent_url: Optional[str]
    created_at: datetime

@dataclass
class ImageAuditRecord:
    """图片审核记录"""
    id: int
    ip_address: str
    mac_address: str
    image_hash: str
    image: str
    audit_result: Optional[str]
    reasons: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # 关联设备信息
    location: Optional[str] = None
    device_id: Optional[str] = None
    device_status: Optional[str] = None

@dataclass
class DeviceInfo:
    """设备信息"""
    id: int
    ip_address: str
    mac_address: str
    location: Optional[str]
    device_id: str
    status: str
    power_control: bool
    network_type: Optional[str]
    sn: Optional[str]
    capture_gap: int
    cold_time: int
    hbtime: int
    configuration: Optional[str]
    strategy_type: Optional[str]
    strategy_contents: Optional[str]
    hurl: Optional[str]
    iurl: Optional[str]
    apssid: Optional[str]
    appass: Optional[str]
    create_time: datetime

@dataclass
class ReviewTask:
    """审核任务"""
    id: str
    name: str
    description: Optional[str]
    strategy_type: Optional[str]
    strategy_contents: Optional[str]
    video_frame_interval: int
    status: str
    progress: int
    error_message: Optional[str]
    total_files: int
    processed_files: int
    violation_count: int
    creator_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

@dataclass
class ReviewFile:
    """审核文件"""
    id: str
    task_id: str
    original_name: str
    file_path: str
    file_type: str
    file_size: int
    mime_type: Optional[str]
    file_extension: Optional[str]
    content_hash: Optional[str]
    page_count: Optional[int]
    duration: Optional[int]
    status: str
    progress: int
    error_message: Optional[str]
    ocr_blocks_count: int
    text_blocks_count: int
    image_blocks_count: int
    violation_count: int
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]

@dataclass
class ReviewResult:
    """审核结果"""
    id: str
    file_id: str
    violation_type: str
    source_type: str
    confidence_score: float
    evidence: Optional[str]
    evidence_text: Optional[str]
    position: Optional[Dict]
    page_number: Optional[int]
    timestamp: Optional[float]
    model_name: Optional[str]
    model_version: Optional[str]
    raw_response: Optional[Dict]
    is_reviewed: bool
    reviewer_id: Optional[str]
    review_result: Optional[str]
    review_comment: Optional[str]
    review_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

@dataclass
class OverviewStats:
    """整体概览统计"""
    url_audit: StatResult
    image_audit: StatResult
    multimedia_audit: Dict[str, Any]
    summary: Dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class LocationStats:
    """位置统计信息"""
    location: str
    total_count: int
    violation_count: int
    violation_rate: float
    device_count: int
    active_device_count: int

@dataclass
class DeviceStats:
    """设备统计信息"""
    device_id: str
    location: str
    ip_address: str
    mac_address: str
    total_count: int
    violation_count: int
    violation_rate: float
    status: str
    last_activity: Optional[datetime]

@dataclass
class FileTypeStats:
    """文件类型统计"""
    file_type: str
    count: int
    total_size: int
    violation_count: int
    violation_rate: float
    avg_size: float
    avg_processing_time: Optional[float] = None

@dataclass
class TimeSeriesPoint:
    """时间序列数据点"""
    date: datetime
    total_count: int
    violation_count: int
    violation_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ViolationTrend:
    """违规趋势数据"""
    violation_type: str
    time_series: List[TimeSeriesPoint]
    total_count: int
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    trend_percentage: float

@dataclass
class ProcessingMetrics:
    """处理性能指标"""
    avg_processing_time: float
    max_processing_time: float
    min_processing_time: float
    success_rate: float
    error_rate: float
    throughput: float  # items per hour
    
@dataclass
class QualityMetrics:
    """质量指标"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    false_negative_rate: float

@dataclass
class SystemHealth:
    """系统健康状态"""
    total_audits_today: int
    total_violations_today: int
    system_uptime: float
    error_rate: float
    avg_response_time: float
    active_devices: int
    pending_tasks: int
    
@dataclass
class ExportRequest:
    """导出请求"""
    format: str  # 'excel', 'csv', 'pdf'
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    include_charts: bool = True
    include_details: bool = True
    filename: Optional[str] = None

@dataclass
class APIResponse:
    """API响应基础类"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: Optional[float] = None

def create_stat_result(total: int, violations: int, breakdown: Dict[str, int] = None) -> StatResult:
    """创建统计结果对象的辅助函数"""
    if breakdown is None:
        breakdown = {}
    
    return StatResult(
        total_count=total,
        violation_count=violations,
        violation_rate=violations / total if total > 0 else 0.0,
        breakdown=breakdown
    )

def create_api_response(success: bool, data: Any = None, error: str = None) -> APIResponse:
    """创建API响应对象的辅助函数"""
    return APIResponse(
        success=success,
        data=data,
        error=error
    )