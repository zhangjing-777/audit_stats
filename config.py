
"""
配置文件
包含数据库配置、日志配置等系统配置信息
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 数据库配置
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'minconn': 1,
    'maxconn': 10
}

# 日志配置
LOG_CONFIG = {
    'level': logging.INFO,
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_file': 'audit_stats.log',
    'encoding': 'utf-8'
}

# 输出目录配置
OUTPUT_CONFIG = {
    'visualization_dir': 'visualizations',
    'report_dir': 'reports',
    'log_dir': 'logs'
}

# 违规类型映射配置
VIOLATION_PATTERNS = {
    '涉黄': [
        r'涉黄', r'涉.*?黄', r'夜场招聘', r'成人交友', r'穿着暴露', 
        r'色情', r'低俗', r'不雅', r'暴露', r'性.*?描述'
    ],
    '涉政': [
        r'涉政', r'政治', r'政府', r'推翻.*?政权', r'反抗', r'政治敏感',
        r'台湾独立', r'港独', r'六四', r'八九', r'法轮大法'
    ],
    '涉恐': [
        r'涉恐', r'恐怖', r'爆炸', r'暴力', r'危险现场', r'袭击',
        r'制造.*?装置', r'恐怖组织'
    ],
    '恶意辱骂': [
        r'恶意辱骂', r'辱骂', r'废物', r'垃圾', r'全家.*?死',
        r'骂人', r'侮辱'
    ],
    '虚假诈骗': [
        r'虚假诈骗', r'诈骗', r'中奖.*?万', r'转账.*?手续费',
        r'投资理财.*?零风险', r'虚假宣传', r'误导'
    ],
    '广告推广': [
        r'广告推广', r'限时秒杀', r'立即抢购', r'全网最低价',
        r'马上下单', r'限时优惠'
    ],
    '违禁词': [
        r'违禁', r'白粉批发', r'军用枪械', r'枪支', r'毒品',
        r'违禁物品'
    ],
    '舆情极端': [
        r'舆情极端', r'社会不公', r'民不聊生', r'起来反抗',
        r'推翻暴政', r'极端情绪'
    ],
    '黑名单词': [
        r'黑名单', r'台湾独立', r'自由民主.*?台湾国', r'港独运动',
        r'香港不是中国'
    ],
    '地图问题': [
        r'地图问题', r'边界', r'国界', r'领土', r'地图.*?错误'
    ]
}

# API配置
API_CONFIG = {
    'default_page_size': 100,
    'max_query_days': 365,
    'timeout_seconds': 300
}

# 可视化配置
VISUALIZATION_CONFIG = {
    'figure_size': (12, 8),
    'dpi': 300,
    'style': 'seaborn-v0_8',
    'colors': {
        'primary': '#1f77b4',
        'secondary': '#ff7f0e',
        'success': '#2ca02c',
        'warning': '#ff7f0e',
        'danger': '#d62728'
    },
    'font_config': {
        'family': ['SimHei', 'Arial Unicode MS', 'DejaVu Sans'],
        'size': 10
    }
}

# 报告配置
REPORT_CONFIG = {
    'excel_engine': 'xlsxwriter',
    'csv_encoding': 'utf-8-sig',
    'pdf_font': 'SimHei',
    'pdf_font_size': 12,
    'company_name': '内容审核系统',
    'report_title': '内容审核统计分析报告'
}

def setup_logging():
    """设置日志配置"""
    # 创建日志目录
    os.makedirs(OUTPUT_CONFIG['log_dir'], exist_ok=True)
    
    log_file = os.path.join(OUTPUT_CONFIG['log_dir'], LOG_CONFIG['log_file'])
    
    logging.basicConfig(
        level=LOG_CONFIG['level'],
        format=LOG_CONFIG['format'],
        handlers=[
            logging.FileHandler(log_file, encoding=LOG_CONFIG['encoding']),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def get_timestamp():
    """获取当前时间戳字符串"""
    return datetime.now().strftime('%Y%m%d_%H%M%S')

def validate_date_range(start_date: str, end_date: str) -> bool:
    """验证日期范围"""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start > end:
            return False
        
        days_diff = (end - start).days
        if days_diff > API_CONFIG['max_query_days']:
            return False
        
        return True
    except ValueError:
        return False

# 初始化配置
logger = setup_logging()

logger.info("配置文件加载完成")
logger.info(f"数据库配置: {DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}")
