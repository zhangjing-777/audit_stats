
"""
报告导出器模块 - 完整版
负责导出Excel、CSV、PDF格式的统计报告
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics import renderPDF
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import io
import base64

from config import OUTPUT_CONFIG, REPORT_CONFIG

logger = logging.getLogger(__name__)

class ReportExporter:
    """报告导出器"""
    
    def __init__(self, output_dir: str = None):
        """初始化导出器
        
        Args:
            output_dir: 输出目录，默认使用配置中的目录
        """
        self.output_dir = output_dir or OUTPUT_CONFIG['report_dir']
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 设置PDF中文字体
        self._setup_pdf_fonts()
        
        # 获取PDF样式
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        logger.info(f"报告导出器初始化完成，输出目录: {self.output_dir}")
    
    def _setup_pdf_fonts(self):
        """设置PDF中文字体"""
        try:
            # 尝试注册中文字体
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',  # macOS 苹方
                '/System/Library/Fonts/Helvetica.ttc',  # macOS
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',  # Linux
                'C:\\Windows\\Fonts\\msyh.ttc',  # Windows 微软雅黑
                'C:\\Windows\\Fonts\\simsun.ttc',  # Windows 宋体
                'C:\\Windows\\Fonts\\simhei.ttf'   # Windows 黑体
            ]
            
            self.chinese_font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Chinese', font_path))
                        self.chinese_font_registered = True
                        logger.debug(f"成功注册中文字体: {font_path}")
                        break
                    except Exception as e:
                        logger.debug(f"注册字体失败 {font_path}: {e}")
                        continue
            
            if not self.chinese_font_registered:
                logger.warning("未找到中文字体，PDF可能无法正确显示中文，将使用默认字体")
                
        except Exception as e:
            logger.warning(f"PDF字体设置失败: {e}")
            self.chinese_font_registered = False
    
    def _setup_custom_styles(self):
        """设置自定义样式"""
        # 标题样式
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # 居中
            fontName='Chinese' if self.chinese_font_registered else 'Helvetica-Bold'
        )
        
        # 章节标题样式
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            fontName='Chinese' if self.chinese_font_registered else 'Helvetica-Bold'
        )
        
        # 小标题样式
        self.subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            fontName='Chinese' if self.chinese_font_registered else 'Helvetica-Bold'
        )
        
        # 正文样式
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            fontName='Chinese' if self.chinese_font_registered else 'Helvetica'
        )
    
    def export_excel_report(self, stats_data: Dict[str, Any], filename: str = None) -> str:
        """导出Excel格式报告
        
        Args:
            stats_data: 统计数据
            filename: 输出文件名
            
        Returns:
            生成的文件路径
        """
        logger.info("开始导出Excel报告")
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'audit_report_{timestamp}.xlsx'
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with pd.ExcelWriter(filepath, engine=REPORT_CONFIG['excel_engine']) as writer:
                # 1. 整体概览工作表
                self._write_overview_sheet(writer, stats_data)
                
                # 2. URL审核详情工作表
                if 'url_audit' in stats_data:
                    self._write_url_audit_sheet(writer, stats_data['url_audit'])
                
                # 3. 图片审核详情工作表
                if 'image_audit' in stats_data:
                    self._write_image_audit_sheet(writer, stats_data['image_audit'])
                
                # 4. 多媒体审核详情工作表
                if 'multimedia_audit' in stats_data:
                    self._write_multimedia_audit_sheet(writer, stats_data['multimedia_audit'])
                
                # 5. 违规类型统计工作表
                self._write_violation_types_sheet(writer, stats_data)
                
                # 6. 性能指标工作表
                self._write_performance_sheet(writer, stats_data)
            
            logger.info(f"Excel报告导出完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"导出Excel报告失败: {e}")
            raise
    
    def _write_overview_sheet(self, writer: pd.ExcelWriter, stats_data: Dict[str, Any]):
        """写入整体概览工作表"""
        if 'overview' not in stats_data:
            return
        
        overview = stats_data['overview']
        overview_data = []
        
        # 添加报告基本信息
        overview_data.append(['报告标题', REPORT_CONFIG['report_title']])
        overview_data.append(['生成时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        overview_data.append(['生成机构', REPORT_CONFIG['company_name']])
        overview_data.append(['', ''])  # 空行
        
        # URL审核统计
        if 'url_audit' in overview:
            url_data = overview['url_audit']
            overview_data.extend([
                ['URL审核统计', ''],
                ['总审核数', f"{url_data.get('total', 0):,}"],
                ['违规数', f"{url_data.get('violations', 0):,}"],
                ['合规数', f"{url_data.get('compliant', 0):,}"],
                ['不确定数', f"{url_data.get('uncertain', 0):,}"],
                ['违规率', f"{url_data.get('violation_rate', 0):.2%}"],
                ['', '']
            ])
        
        # 图片审核统计
        if 'image_audit' in overview:
            image_data = overview['image_audit']
            overview_data.extend([
                ['图片审核统计', ''],
                ['总审核数', f"{image_data.get('total', 0):,}"],
                ['违规数', f"{image_data.get('violations', 0):,}"],
                ['合规数', f"{image_data.get('compliant', 0):,}"],
                ['失败数', f"{image_data.get('failed', 0):,}"],
                ['违规率', f"{image_data.get('violation_rate', 0):.2%}"],
                ['覆盖设备数', f"{image_data.get('device_count', 0):,}"],
                ['覆盖位置数', f"{image_data.get('location_count', 0):,}"],
                ['', '']
            ])
        
        # 多媒体审核统计
        if 'multimedia_audit' in overview:
            multimedia_data = overview['multimedia_audit']
            overview_data.extend([
                ['多媒体审核统计', ''],
                ['总任务数', f"{multimedia_data.get('total_tasks', 0):,}"],
                ['已完成任务', f"{multimedia_data.get('completed_tasks', 0):,}"],
                ['待处理任务', f"{multimedia_data.get('pending_tasks', 0):,}"],
                ['失败任务', f"{multimedia_data.get('failed_tasks', 0):,}"],
                ['完成率', f"{multimedia_data.get('completion_rate', 0):.2%}"],
                ['总文件数', f"{multimedia_data.get('total_files', 0):,}"],
                ['总违规数', f"{multimedia_data.get('total_violations', 0):,}"],
                ['', '']
            ])
        
        # 系统总结
        if 'summary' in overview:
            summary = overview['summary']
            overview_data.extend([
                ['系统总结', ''],
                ['总审核量', f"{summary.get('total_audits', 0):,}"],
                ['总违规数', f"{summary.get('total_violations', 0):,}"],
                ['整体违规率', f"{summary.get('overall_violation_rate', 0):.2%}"],
                ['主要审核类型', summary.get('most_active_audit_type', '未知')]
            ])
        
        df = pd.DataFrame(overview_data, columns=['指标', '数值'])
        df.to_excel(writer, sheet_name='整体概览', index=False)
    
    def _write_url_audit_sheet(self, writer: pd.ExcelWriter, url_data: Dict[str, Any]):
        """写入URL审核详情工作表"""
        # 基本统计
        basic_stats = [
            ['总审核数', f"{url_data.get('total_count', 0):,}"],
            ['违规数', f"{url_data.get('violation_count', 0):,}"],
            ['违规率', f"{url_data.get('violation_rate', 0):.2%}"]
        ]
        basic_df = pd.DataFrame(basic_stats, columns=['指标', '数值'])
        basic_df.to_excel(writer, sheet_name='URL审核详情', index=False, startrow=0)
        
        # 违规类型统计
        if 'violation_types' in url_data and url_data['violation_types']:
            violation_data = [[vtype, count] for vtype, count in url_data['violation_types'].items()]
            violation_df = pd.DataFrame(violation_data, columns=['违规类型', '数量'])
            violation_df = violation_df.sort_values('数量', ascending=False)
            violation_df.to_excel(writer, sheet_name='URL审核详情', index=False, startrow=len(basic_stats) + 3)
        
        # 时间趋势
        if 'time_series' in url_data and url_data['time_series']:
            time_df = pd.DataFrame(url_data['time_series'])
            time_df.to_excel(writer, sheet_name='URL时间趋势', index=False)
        
        # TOP违规原因
        if 'top_violation_reasons' in url_data and url_data['top_violation_reasons']:
            top_reasons_data = []
            for reason_info in url_data['top_violation_reasons']:
                top_reasons_data.append([
                    reason_info['reason'],
                    reason_info['count'],
                    f"{reason_info['percentage']:.2%}",
                    '; '.join(reason_info.get('examples', [])[:3])
                ])
            
            top_df = pd.DataFrame(top_reasons_data, columns=['违规原因', '数量', '占比', '示例URL'])
            top_df.to_excel(writer, sheet_name='TOP违规原因', index=False)
    
    def _write_image_audit_sheet(self, writer: pd.ExcelWriter, image_data: Dict[str, Any]):
        """写入图片审核详情工作表"""
        # 基本统计
        basic_stats = [
            ['总审核数', f"{image_data.get('total_count', 0):,}"],
            ['违规数', f"{image_data.get('violation_count', 0):,}"],
            ['违规率', f"{image_data.get('violation_rate', 0):.2%}"],
            ['失败数', f"{image_data.get('failed_count', 0):,}"],
            ['成功率', f"{image_data.get('success_rate', 0):.2%}"]
        ]
        basic_df = pd.DataFrame(basic_stats, columns=['指标', '数值'])
        basic_df.to_excel(writer, sheet_name='图片审核详情', index=False)
        
        # 位置统计
        if 'location_stats' in image_data and image_data['location_stats']:
            location_data = []
            for location, stats in image_data['location_stats'].items():
                location_data.append([
                    location,
                    stats['total'],
                    stats['violations'],
                    f"{stats['violation_rate']:.2%}",
                    stats.get('device_count', 0)
                ])
            
            location_df = pd.DataFrame(location_data, columns=['位置', '总数', '违规数', '违规率', '设备数'])
            location_df = location_df.sort_values('总数', ascending=False)
            location_df.to_excel(writer, sheet_name='位置统计', index=False)
        
        # 设备统计
        if 'device_stats' in image_data and image_data['device_stats']:
            device_data = []
            for device_id, stats in image_data['device_stats'].items():
                device_data.append([
                    device_id,
                    stats.get('location', ''),
                    stats.get('ip_address', ''),
                    stats['total'],
                    stats['violations'],
                    f"{stats['violation_rate']:.2%}",
                    stats.get('status', '')
                ])
            
            device_df = pd.DataFrame(device_data, columns=['设备ID', '位置', 'IP地址', '总数', '违规数', '违规率', '状态'])
            device_df = device_df.sort_values('违规数', ascending=False)
            device_df.to_excel(writer, sheet_name='设备统计', index=False)
    
    def _write_multimedia_audit_sheet(self, writer: pd.ExcelWriter, multimedia_data: Dict[str, Any]):
        """写入多媒体审核详情工作表"""
        # 任务统计
        if 'task_stats' in multimedia_data:
            task_stats = multimedia_data['task_stats']
            task_data = [[key, value] for key, value in task_stats.items()]
            task_df = pd.DataFrame(task_data, columns=['指标', '数值'])
            task_df.to_excel(writer, sheet_name='多媒体任务统计', index=False)
        
        # 文件类型统计
        if 'file_stats' in multimedia_data and 'file_type_distribution' in multimedia_data['file_stats']:
            file_types = multimedia_data['file_stats']['file_type_distribution']
            if file_types:
                file_data = []
                for file_type_info in file_types:
                    file_data.append([
                        file_type_info['file_type'],
                        file_type_info['count'],
                        f"{file_type_info['total_size']:,}",
                        file_type_info['violations']
                    ])
                
                file_df = pd.DataFrame(file_data, columns=['文件类型', '数量', '总大小(字节)', '违规数'])
                file_df.to_excel(writer, sheet_name='文件类型统计', index=False)
        
        # 违规类型统计
        if 'result_stats' in multimedia_data and 'violation_distribution' in multimedia_data['result_stats']:
            violations = multimedia_data['result_stats']['violation_distribution']
            if violations:
                violation_data = []
                for violation_info in violations:
                    violation_data.append([
                        violation_info['violation_type'],
                        violation_info['count'],
                        f"{violation_info.get('avg_confidence', 0):.2f}"
                    ])
                
                violation_df = pd.DataFrame(violation_data, columns=['违规类型', '数量', '平均置信度'])
                violation_df.to_excel(writer, sheet_name='多媒体违规统计', index=False)
    
    def _write_violation_types_sheet(self, writer: pd.ExcelWriter, stats_data: Dict[str, Any]):
        """写入违规类型汇总工作表"""
        all_violations = {}
        
        # 收集各类审核的违规类型
        if 'url_audit' in stats_data and 'violation_types' in stats_data['url_audit']:
            for vtype, count in stats_data['url_audit']['violation_types'].items():
                if vtype not in all_violations:
                    all_violations[vtype] = {'URL审核': 0, '图片审核': 0, '多媒体审核': 0}
                all_violations[vtype]['URL审核'] = count
        
        if 'image_audit' in stats_data and 'violation_types' in stats_data['image_audit']:
            for vtype, count in stats_data['image_audit']['violation_types'].items():
                if vtype not in all_violations:
                    all_violations[vtype] = {'URL审核': 0, '图片审核': 0, '多媒体审核': 0}
                all_violations[vtype]['图片审核'] = count
        
        if 'multimedia_audit' in stats_data and 'result_stats' in stats_data['multimedia_audit']:
            if 'violation_distribution' in stats_data['multimedia_audit']['result_stats']:
                for violation_info in stats_data['multimedia_audit']['result_stats']['violation_distribution']:
                    vtype = violation_info['violation_type']
                    count = violation_info['count']
                    if vtype not in all_violations:
                        all_violations[vtype] = {'URL审核': 0, '图片审核': 0, '多媒体审核': 0}
                    all_violations[vtype]['多媒体审核'] = count
        
        # 构建汇总数据
        if all_violations:
            violation_summary = []
            for vtype, counts in all_violations.items():
                total = sum(counts.values())
                violation_summary.append([
                    vtype,
                    counts['URL审核'],
                    counts['图片审核'],
                    counts['多媒体审核'],
                    total
                ])
            
            summary_df = pd.DataFrame(violation_summary, 
                                    columns=['违规类型', 'URL审核', '图片审核', '多媒体审核', '总计'])
            summary_df = summary_df.sort_values('总计', ascending=False)
            summary_df.to_excel(writer, sheet_name='违规类型汇总', index=False)
    
    def _write_performance_sheet(self, writer: pd.ExcelWriter, stats_data: Dict[str, Any]):
        """写入性能指标工作表"""
        performance_data = []
        
        # URL审核性能
        if 'url_audit' in stats_data and 'processing_metrics' in stats_data['url_audit']:
            metrics = stats_data['url_audit']['processing_metrics']
            performance_data.extend([
                ['URL审核性能', ''],
                ['平均处理时间(秒)', f"{metrics.get('avg_processing_time', 0):.3f}"],
                ['处理量', f"{metrics.get('throughput', 0):,}"],
                ['成功率', f"{metrics.get('success_rate', 0):.2%}"],
                ['错误率', f"{metrics.get('error_rate', 0):.2%}"],
                ['', '']
            ])
        
        # 图片审核性能
        if 'image_audit' in stats_data:
            image_data = stats_data['image_audit']
            performance_data.extend([
                ['图片审核性能', ''],
                ['总处理数', f"{image_data.get('total_count', 0):,}"],
                ['成功率', f"{image_data.get('success_rate', 0):.2%}"],
                ['失败数', f"{image_data.get('failed_count', 0):,}"],
                ['', '']
            ])
        
        # 多媒体审核性能
        if 'multimedia_audit' in stats_data and 'processing_metrics' in stats_data['multimedia_audit']:
            metrics = stats_data['multimedia_audit']['processing_metrics']
            performance_data.extend([
                ['多媒体审核性能', ''],
                ['平均任务耗时(秒)', f"{metrics.get('avg_task_duration', 0):.1f}"],
                ['最大任务耗时(秒)', f"{metrics.get('max_task_duration', 0):.1f}"],
                ['最小任务耗时(秒)', f"{metrics.get('min_task_duration', 0):.1f}"],
                ['任务成功率', f"{metrics.get('success_rate', 0):.2%}"]
            ])
        
        if performance_data:
            performance_df = pd.DataFrame(performance_data, columns=['指标', '数值'])
            performance_df.to_excel(writer, sheet_name='性能指标', index=False)
    
    def export_csv_report(self, stats_data: Dict[str, Any], filename: str = None) -> str:
        """导出CSV格式报告
        
        Args:
            stats_data: 统计数据
            filename: 输出文件名
            
        Returns:
            生成的文件路径
        """
        logger.info("开始导出CSV报告")
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'audit_summary_{timestamp}.csv'
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # 构建汇总数据
            summary_data = []
            
            if 'overview' in stats_data:
                overview = stats_data['overview']
                
                # 添加各类审核的汇总
                audit_types = [
                    ('URL审核', overview.get('url_audit', {})),
                    ('图片审核', overview.get('image_audit', {})),
                ]
                
                for audit_type, data in audit_types:
                    if data and data.get('total', 0) > 0:
                        summary_data.append([
                            audit_type,
                            data.get('total', 0),
                            data.get('violations', 0),
                            f"{data.get('violation_rate', 0):.2%}",
                            data.get('compliant', data.get('total', 0) - data.get('violations', 0)),
                            datetime.now().strftime('%Y-%m-%d')
                        ])
                
                # 添加多媒体审核数据
                if 'multimedia_audit' in overview:
                    multimedia = overview['multimedia_audit']
                    summary_data.append([
                        '多媒体审核',
                        multimedia.get('total_tasks', 0),
                        multimedia.get('total_violations', 0),
                        f"{multimedia.get('total_violations', 0) / max(multimedia.get('total_files', 1), 1):.2%}",
                        multimedia.get('completed_tasks', 0),
                        datetime.now().strftime('%Y-%m-%d')
                    ])
            
            # 创建DataFrame并保存
            df = pd.DataFrame(summary_data, columns=['审核类型', '总数', '违规数', '违规率', '合规/完成数', '统计日期'])
            df.to_csv(filepath, index=False, encoding=REPORT_CONFIG['csv_encoding'])
            
            logger.info(f"CSV报告导出完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"导出CSV报告失败: {e}")
            raise
    
    def export_pdf_report(self, stats_data: Dict[str, Any], chart_files: List[str] = None, filename: str = None) -> str:
        """导出PDF格式报告
        
        Args:
            stats_data: 统计数据
            chart_files: 图表文件路径列表
            filename: 输出文件名
            
        Returns:
            生成的文件路径
        """
        logger.info("开始导出PDF报告")
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'audit_report_{timestamp}.pdf'
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # 创建PDF文档
            doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
            story = []
            
            # 1. 标题页
            story.append(Paragraph(REPORT_CONFIG['report_title'], self.title_style))
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}", self.normal_style))
            story.append(Paragraph(f"生成机构: {REPORT_CONFIG['company_name']}", self.normal_style))
            story.append(Spacer(1, 0.8*inch))
            
            # 2. 执行摘要
            if 'overview' in stats_data:
                story.append(Paragraph("执行摘要", self.heading_style))
                summary_text = self._generate_pdf_summary(stats_data['overview'])
                story.append(Paragraph(summary_text, self.normal_style))
                story.append(Spacer(1, 0.5*inch))
            
            # 3. 关键指标仪表板
            story.append(Paragraph("关键指标概览", self.heading_style))
            if 'overview' in stats_data and 'summary' in stats_data['overview']:
                summary = stats_data['overview']['summary']
                
                # 创建关键指标表格
                kpi_data = [
                    ['指标', '数值', '说明'],
                    ['总审核量', f"{summary.get('total_audits', 0):,}", '所有类型审核的总数量'],
                    ['总违规数', f"{summary.get('total_violations', 0):,}", '发现的违规内容总数'],
                    ['整体违规率', f"{summary.get('overall_violation_rate', 0):.2%}", '违规内容占总审核量的比例'],
                    ['主要审核类型', summary.get('most_active_audit_type', '未知'), '审核量最大的类型']
                ]
                
                kpi_table = Table(kpi_data, colWidths=[4*cm, 3*cm, 6*cm])
                kpi_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Chinese' if self.chinese_font_registered else 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('FONTNAME', (0, 1), (-1, -1), 'Chinese' if self.chinese_font_registered else 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                story.append(kpi_table)
                story.append(Spacer(1, 0.3*inch))
            
            # 4. 详细统计表格
            story.append(Paragraph("详细统计数据", self.heading_style))
            
            # URL审核表格
            if 'url_audit' in stats_data:
                story.append(Paragraph("URL审核统计", self.subheading_style))
                url_table = self._create_url_audit_table(stats_data['url_audit'])
                if url_table:
                    story.append(url_table)
                story.append(Spacer(1, 0.3*inch))
            
            # 图片审核表格
            if 'image_audit' in stats_data:
                story.append(Paragraph("图片审核统计", self.subheading_style))
                image_table = self._create_image_audit_table(stats_data['image_audit'])
                if image_table:
                    story.append(image_table)
                story.append(Spacer(1, 0.3*inch))
            
            # 多媒体审核表格
            if 'multimedia_audit' in stats_data:
                story.append(Paragraph("多媒体审核统计", self.subheading_style))
                multimedia_table = self._create_multimedia_audit_table(stats_data['multimedia_audit'])
                if multimedia_table:
                    story.append(multimedia_table)
                story.append(Spacer(1, 0.3*inch))
            
            # 5. 违规类型分析
            story.append(Paragraph("违规类型分析", self.heading_style))
            violation_analysis_table = self._create_violation_analysis_table(stats_data)
            if violation_analysis_table:
                story.append(violation_analysis_table)
                story.append(Spacer(1, 0.3*inch))
            
            # 6. 位置和设备分析（如果有图片审核数据）
            if 'image_audit' in stats_data and 'location_stats' in stats_data['image_audit']:
                story.append(Paragraph("位置与设备分析", self.heading_style))
                location_table = self._create_location_analysis_table(stats_data['image_audit'])
                if location_table:
                    story.append(location_table)
                    story.append(Spacer(1, 0.3*inch))
            
            # 7. 图表部分
            if chart_files:
                story.append(PageBreak())  # 新页面开始图表
                story.append(Paragraph("统计图表", self.heading_style))
                
                for i, chart_file in enumerate(chart_files):
                    if os.path.exists(chart_file) and chart_file.lower().endswith('.png'):
                        try:
                            # 获取图片名称作为标题
                            chart_name = os.path.basename(chart_file).replace('.png', '').replace('_', ' ').title()
                            story.append(Paragraph(f"图表 {i+1}: {chart_name}", self.subheading_style))
                            
                            # 添加图片到PDF
                            img = Image(chart_file, width=6*inch, height=4*inch)
                            story.append(img)
                            story.append(Spacer(1, 0.3*inch))
                            
                            # 每两个图表分页
                            if (i + 1) % 2 == 0 and i < len(chart_files) - 1:
                                story.append(PageBreak())
                                
                        except Exception as e:
                            logger.warning(f"无法添加图表到PDF: {chart_file}, 错误: {e}")
                            story.append(Paragraph(f"图表加载失败: {chart_name}", self.normal_style))
                            story.append(Spacer(1, 0.2*inch))
            
            # 8. 趋势分析
            if 'url_audit' in stats_data and 'time_series' in stats_data['url_audit']:
                story.append(PageBreak())
                story.append(Paragraph("趋势分析", self.heading_style))
                trend_analysis = self._generate_trend_analysis(stats_data['url_audit']['time_series'])
                story.append(Paragraph(trend_analysis, self.normal_style))
                story.append(Spacer(1, 0.3*inch))
            
            # 9. 性能分析
            story.append(Paragraph("系统性能分析", self.heading_style))
            performance_analysis = self._generate_performance_analysis(stats_data)
            story.append(Paragraph(performance_analysis, self.normal_style))
            story.append(Spacer(1, 0.3*inch))
            
            # 10. 结论和建议
            story.append(PageBreak())
            story.append(Paragraph("结论与建议", self.heading_style))
            conclusions = self._generate_conclusions(stats_data)
            story.append(Paragraph(conclusions, self.normal_style))
            story.append(Spacer(1, 0.3*inch))
            
            # 11. 附录 - 技术说明
            story.append(Paragraph("附录：技术说明", self.heading_style))
            technical_notes = self._generate_technical_notes()
            story.append(Paragraph(technical_notes, self.normal_style))
            
            # 构建PDF
            doc.build(story)
            
            logger.info(f"PDF报告导出完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"导出PDF报告失败: {e}")
            raise
    
    def _generate_pdf_summary(self, overview: Dict[str, Any]) -> str:
        """生成PDF摘要文本"""
        summary_parts = []
        
        if 'url_audit' in overview:
            url_data = overview['url_audit']
            summary_parts.append(f"URL审核方面，系统共处理了 {url_data.get('total', 0):,} 条记录，其中发现违规内容 {url_data.get('violations', 0):,} 条，违规率为 {url_data.get('violation_rate', 0):.2%}。")
        
        if 'image_audit' in overview:
            image_data = overview['image_audit']
            summary_parts.append(f"图片审核方面，系统共处理了 {image_data.get('total', 0):,} 张图片，发现违规图片 {image_data.get('violations', 0):,} 张，违规率为 {image_data.get('violation_rate', 0):.2%}，审核覆盖了 {image_data.get('device_count', 0)} 台设备。")
        
        if 'multimedia_audit' in overview:
            multimedia_data = overview['multimedia_audit']
            summary_parts.append(f"多媒体审核方面，系统共处理了 {multimedia_data.get('total_tasks', 0):,} 个审核任务，任务完成率为 {multimedia_data.get('completion_rate', 0):.2%}，共审核了 {multimedia_data.get('total_files', 0):,} 个文件，发现违规内容 {multimedia_data.get('total_violations', 0):,} 处。")
        
        if 'summary' in overview:
            summary = overview['summary']
            summary_parts.append(f"系统整体审核量达到 {summary.get('total_audits', 0):,} 次，累计发现违规内容 {summary.get('total_violations', 0):,} 处，系统整体违规率为 {summary.get('overall_violation_rate', 0):.2%}。")
        
        return " ".join(summary_parts)
    
    def _create_url_audit_table(self, url_data: Dict[str, Any]) -> Optional[Table]:
        """创建URL审核统计表格"""
        try:
            data = [['指标', '数值', '说明']]
            data.append(['总审核数', f"{url_data.get('total_count', 0):,}", 'URL内容审核的总记录数'])
            data.append(['违规数', f"{url_data.get('violation_count', 0):,}", '被识别为违规的URL数量'])
            data.append(['违规率', f"{url_data.get('violation_rate', 0):.2%}", '违规内容占总审核量的比例'])
            
            if 'processing_metrics' in url_data:
                metrics = url_data['processing_metrics']
                data.append(['平均处理时间', f"{metrics.get('avg_processing_time', 0):.3f}秒", '单条URL的平均审核时间'])
                data.append(['处理成功率', f"{metrics.get('success_rate', 0):.2%}", '成功完成审核的比例'])
            
            # 添加Top违规类型
            if 'violation_types' in url_data and url_data['violation_types']:
                top_violations = sorted(url_data['violation_types'].items(), key=lambda x: x[1], reverse=True)[:3]
                violation_text = ", ".join([f"{vtype}({count})" for vtype, count in top_violations])
                data.append(['主要违规类型', violation_text, '发现次数最多的违规类型'])
            
            table = Table(data, colWidths=[4*cm, 3*cm, 6*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Chinese' if self.chinese_font_registered else 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Chinese' if self.chinese_font_registered else 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            return table
        except Exception as e:
            logger.warning(f"创建URL审核表格失败: {e}")
            return None
    
    def _create_image_audit_table(self, image_data: Dict[str, Any]) -> Optional[Table]:
        """创建图片审核统计表格"""
        try:
            data = [['指标', '数值', '说明']]
            data.append(['总审核数', f"{image_data.get('total_count', 0):,}", '图片审核的总数量'])
            data.append(['违规数', f"{image_data.get('violation_count', 0):,}", '被识别为违规的图片数量'])
            data.append(['违规率', f"{image_data.get('violation_rate', 0):.2%}", '违规图片占总审核量的比例'])
            data.append(['审核失败数', f"{image_data.get('failed_count', 0):,}", '审核过程中失败的图片数量'])
            data.append(['审核成功率', f"{image_data.get('success_rate', 0):.2%}", '成功完成审核的比例'])
            
            # 设备和位置信息
            if 'location_stats' in image_data:
                location_count = len(image_data['location_stats'])
                data.append(['覆盖位置数', f"{location_count}", '图片审核覆盖的物理位置数量'])
            
            if 'device_stats' in image_data:
                device_count = len(image_data['device_stats'])
                data.append(['监控设备数', f"{device_count}", '参与图片审核的设备数量'])
            
            table = Table(data, colWidths=[4*cm, 3*cm, 6*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Chinese' if self.chinese_font_registered else 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Chinese' if self.chinese_font_registered else 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            return table
        except Exception as e:
            logger.warning(f"创建图片审核表格失败: {e}")
            return None
    
    def _create_multimedia_audit_table(self, multimedia_data: Dict[str, Any]) -> Optional[Table]:
        """创建多媒体审核统计表格"""
        try:
            data = [['指标', '数值', '说明']]
            
            if 'task_stats' in multimedia_data:
                task_stats = multimedia_data['task_stats']
                data.append(['总任务数', f"{task_stats.get('total_tasks', 0):,}", '多媒体审核任务的总数量'])
                data.append(['已完成任务', f"{task_stats.get('completed', 0):,}", '成功完成的审核任务数量'])
                data.append(['进行中任务', f"{task_stats.get('processing', 0):,}", '正在处理中的任务数量'])
                data.append(['待处理任务', f"{task_stats.get('pending', 0):,}", '等待处理的任务数量'])
                data.append(['失败任务', f"{task_stats.get('failed', 0):,}", '处理失败的任务数量'])
                data.append(['任务完成率', f"{task_stats.get('completed', 0) / max(task_stats.get('total_tasks', 1), 1):.2%}", '已完成任务占总任务的比例'])
            
            if 'file_stats' in multimedia_data:
                file_stats = multimedia_data['file_stats']
                data.append(['总文件数', f"{file_stats.get('total_files', 0):,}", '审核涉及的文件总数量'])
                data.append(['文件类型数', f"{file_stats.get('file_types', 0):,}", '涉及的不同文件类型数量'])
                
                total_size = file_stats.get('total_size', 0)
                size_gb = total_size / (1024**3)
                data.append(['总文件大小', f"{size_gb:.2f}GB", '所有审核文件的总大小'])
            
            table = Table(data, colWidths=[4*cm, 3*cm, 6*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Chinese' if self.chinese_font_registered else 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Chinese' if self.chinese_font_registered else 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            return table
        except Exception as e:
            logger.warning(f"创建多媒体审核表格失败: {e}")
            return None
    
    def _create_violation_analysis_table(self, stats_data: Dict[str, Any]) -> Optional[Table]:
        """创建违规类型分析表格"""
        try:
            # 收集所有违规类型
            all_violations = {}
            
            if 'url_audit' in stats_data and 'violation_types' in stats_data['url_audit']:
                for vtype, count in stats_data['url_audit']['violation_types'].items():
                    all_violations[vtype] = all_violations.get(vtype, 0) + count
            
            if 'image_audit' in stats_data and 'violation_types' in stats_data['image_audit']:
                for vtype, count in stats_data['image_audit']['violation_types'].items():
                    all_violations[vtype] = all_violations.get(vtype, 0) + count
            
            if 'multimedia_audit' in stats_data and 'result_stats' in stats_data['multimedia_audit']:
                if 'violation_distribution' in stats_data['multimedia_audit']['result_stats']:
                    for violation_info in stats_data['multimedia_audit']['result_stats']['violation_distribution']:
                        vtype = violation_info['violation_type']
                        count = violation_info['count']
                        all_violations[vtype] = all_violations.get(vtype, 0) + count
            
            if not all_violations:
                return None
            
            # 按数量排序
            sorted_violations = sorted(all_violations.items(), key=lambda x: x[1], reverse=True)
            
            data = [['违规类型', '发现次数', '风险等级', '建议措施']]
            
            # 风险等级判断
            total_violations = sum(all_violations.values())
            for vtype, count in sorted_violations[:10]:  # 只显示前10个
                percentage = count / total_violations
                if percentage > 0.3:
                    risk_level = "高风险"
                    suggestion = "需要立即加强监管和处理"
                elif percentage > 0.1:
                    risk_level = "中风险"
                    suggestion = "建议加强关注和预防"
                else:
                    risk_level = "低风险"
                    suggestion = "保持常规监控"
                
                data.append([vtype, f"{count:,}", risk_level, suggestion])
            
            table = Table(data, colWidths=[3*cm, 2.5*cm, 2*cm, 5.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Chinese' if self.chinese_font_registered else 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Chinese' if self.chinese_font_registered else 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            # 根据风险等级设置行颜色
            for i, (vtype, count) in enumerate(sorted_violations[:10], 1):
                percentage = count / total_violations
                if percentage > 0.3:
                    color = colors.lightcoral
                elif percentage > 0.1:
                    color = colors.lightyellow
                else:
                    color = colors.lightgreen
                table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), color)]))
            
            return table
        except Exception as e:
            logger.warning(f"创建违规分析表格失败: {e}")
            return None
    
    def _create_location_analysis_table(self, image_data: Dict[str, Any]) -> Optional[Table]:
        """创建位置分析表格"""
        try:
            if 'location_stats' not in image_data:
                return None
            
            location_stats = image_data['location_stats']
            if not location_stats:
                return None
            
            # 按违规率排序
            sorted_locations = sorted(location_stats.items(), 
                                    key=lambda x: x[1]['violation_rate'], reverse=True)
            
            data = [['位置', '总审核数', '违规数', '违规率', '设备数', '风险评估']]
            
            for location, stats in sorted_locations:
                violation_rate = stats['violation_rate']
                if violation_rate > 0.2:
                    risk_assessment = "高风险区域"
                elif violation_rate > 0.1:
                    risk_assessment = "中风险区域"
                else:
                    risk_assessment = "低风险区域"
                
                data.append([
                    location,
                    f"{stats['total']:,}",
                    f"{stats['violations']:,}",
                    f"{violation_rate:.2%}",
                    f"{stats.get('device_count', 0)}",
                    risk_assessment
                ])
            
            table = Table(data, colWidths=[3*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Chinese' if self.chinese_font_registered else 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Chinese' if self.chinese_font_registered else 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            return table
        except Exception as e:
            logger.warning(f"创建位置分析表格失败: {e}")
            return None
    
    def _generate_trend_analysis(self, time_series: List[Dict]) -> str:
        """生成趋势分析文本"""
        if not time_series or len(time_series) < 2:
            return "数据不足，无法进行趋势分析。"
        
        # 计算趋势
        recent_data = time_series[-7:]  # 最近7天
        early_data = time_series[:7] if len(time_series) >= 14 else time_series[:len(time_series)//2]
        
        recent_avg_violations = sum(day['daily_violations'] for day in recent_data) / len(recent_data)
        early_avg_violations = sum(day['daily_violations'] for day in early_data) / len(early_data)
        
        recent_avg_total = sum(day['daily_total'] for day in recent_data) / len(recent_data)
        early_avg_total = sum(day['daily_total'] for day in early_data) / len(early_data)
        
        violation_trend = (recent_avg_violations - early_avg_violations) / max(early_avg_violations, 1) * 100
        total_trend = (recent_avg_total - early_avg_total) / max(early_avg_total, 1) * 100
        
        trend_text = f"根据时间序列数据分析，"
        
        if abs(total_trend) > 10:
            trend_text += f"审核总量{'增长' if total_trend > 0 else '下降'}了{abs(total_trend):.1f}%，"
        else:
            trend_text += "审核总量保持相对稳定，"
        
        if abs(violation_trend) > 10:
            trend_text += f"违规数量{'增长' if violation_trend > 0 else '下降'}了{abs(violation_trend):.1f}%。"
        else:
            trend_text += "违规数量变化不大。"
        
        if violation_trend > 20:
            trend_text += "建议加强内容审核策略和监管力度。"
        elif violation_trend < -20:
            trend_text += "违规内容得到有效控制，建议保持当前审核策略。"
        
        return trend_text
    
    def _generate_performance_analysis(self, stats_data: Dict[str, Any]) -> str:
        """生成性能分析文本"""
        performance_text = "系统性能分析：\n\n"
        
        # URL审核性能
        if 'url_audit' in stats_data and 'processing_metrics' in stats_data['url_audit']:
            metrics = stats_data['url_audit']['processing_metrics']
            avg_time = metrics.get('avg_processing_time', 0)
            success_rate = metrics.get('success_rate', 0)
            
            performance_text += f"URL审核性能：平均处理时间 {avg_time:.3f} 秒，成功率 {success_rate:.1%}。"
            
            if avg_time < 1.0:
                performance_text += "处理速度优秀。"
            elif avg_time < 3.0:
                performance_text += "处理速度良好。"
            else:
                performance_text += "建议优化处理流程以提升效率。"
            
            performance_text += "\n\n"
        
        # 图片审核性能
        if 'image_audit' in stats_data:
            success_rate = stats_data['image_audit'].get('success_rate', 0)
            performance_text += f"图片审核性能：审核成功率 {success_rate:.1%}。"
            
            if success_rate > 0.95:
                performance_text += "系统稳定性优秀。"
            elif success_rate > 0.90:
                performance_text += "系统稳定性良好。"
            else:
                performance_text += "建议检查系统稳定性和错误处理机制。"
            
            performance_text += "\n\n"
        
        # 多媒体审核性能
        if 'multimedia_audit' in stats_data and 'processing_metrics' in stats_data['multimedia_audit']:
            metrics = stats_data['multimedia_audit']['processing_metrics']
            avg_duration = metrics.get('avg_task_duration', 0)
            task_success_rate = metrics.get('success_rate', 0)
            
            performance_text += f"多媒体审核性能：平均任务处理时间 {avg_duration/60:.1f} 分钟，任务成功率 {task_success_rate:.1%}。"
            
            if avg_duration < 300:  # 5分钟
                performance_text += "处理效率优秀。"
            elif avg_duration < 1800:  # 30分钟
                performance_text += "处理效率良好。"
            else:
                performance_text += "建议优化多媒体处理算法和资源配置。"
        
        return performance_text
    
    def _generate_conclusions(self, stats_data: Dict[str, Any]) -> str:
        """生成结论和建议"""
        conclusions = []
        
        if 'overview' in stats_data:
            overview = stats_data['overview']
            
            # 分析整体违规率
            if 'summary' in overview:
                overall_rate = overview['summary'].get('overall_violation_rate', 0)
                if overall_rate > 0.15:  # 15%
                    conclusions.append("系统检测到较高的违规率，建议立即采取以下措施：1）加强内容审核策略；2）优化违规检测规则；3）增强人工复核机制；4）加强内容发布前的预防性审查。")
                elif overall_rate > 0.08:  # 8%
                    conclusions.append("系统违规率处于中等水平，建议：1）持续监控违规趋势；2）定期更新审核规则库；3）加强重点区域和设备的监管；4）完善违规内容的处理流程。")
                elif overall_rate > 0.03:  # 3%
                    conclusions.append("系统违规率较低，表明当前审核策略有效，建议：1）保持现有审核标准；2）持续优化检测算法；3）建立长期监控机制；4）定期评估和调整审核策略。")
                else:
                    conclusions.append("系统违规率很低，内容审核效果优秀，建议：1）继续保持高标准的审核质量；2）探索更智能的审核技术；3）建立最佳实践分享机制；4）为其他类似系统提供参考。")
            
            # 分析各类审核效果对比
            if 'url_audit' in overview and 'image_audit' in overview:
                url_rate = overview['url_audit'].get('violation_rate', 0)
                image_rate = overview['image_audit'].get('violation_rate', 0)
                
                if abs(url_rate - image_rate) > 0.05:  # 差异超过5%
                    if url_rate > image_rate:
                        conclusions.append("URL审核违规率明显高于图片审核，建议：1）重点关注文本内容的规范性；2）加强URL来源的可信度验证；3）优化文本违规检测算法；4）建立URL黑白名单机制。")
                    else:
                        conclusions.append("图片审核违规率明显高于URL审核，建议：1）加强图像识别技术的准确性；2）重点监控图片内容的合规性；3）完善图片审核的人工复核流程；4）优化图像违规检测模型。")
            
            # 设备和位置相关建议
            if 'image_audit' in stats_data and 'location_stats' in stats_data['image_audit']:
                location_stats = stats_data['image_audit']['location_stats']
                if location_stats:
                    high_risk_locations = [
                        loc for loc, stats in location_stats.items() 
                        if stats.get('violation_rate', 0) > 0.15
                    ]
                    medium_risk_locations = [
                        loc for loc, stats in location_stats.items() 
                        if 0.08 < stats.get('violation_rate', 0) <= 0.15
                    ]
                    
                    if high_risk_locations:
                        conclusions.append(f"高风险位置识别：{', '.join(high_risk_locations[:5])}等位置违规率较高，建议：1）增加这些位置的审核频率；2）部署额外的监控设备；3）加强现场管理和培训；4）建立专项整改计划。")
                    
                    if medium_risk_locations:
                        conclusions.append(f"中风险位置关注：{', '.join(medium_risk_locations[:5])}等位置需要重点关注，建议定期检查和预防性维护。")
        
        # 技术优化建议
        performance_suggestions = []
        
        if 'url_audit' in stats_data and 'processing_metrics' in stats_data['url_audit']:
            metrics = stats_data['url_audit']['processing_metrics']
            if metrics.get('avg_processing_time', 0) > 2.0:
                performance_suggestions.append("优化URL审核算法以提升处理速度")
            if metrics.get('success_rate', 0) < 0.95:
                performance_suggestions.append("改进错误处理机制以提高审核成功率")
        
        if 'image_audit' in stats_data:
            if stats_data['image_audit'].get('success_rate', 0) < 0.90:
                performance_suggestions.append("优化图片审核系统的稳定性和可靠性")
        
        if performance_suggestions:
            conclusions.append(f"技术优化建议：{'; '.join(performance_suggestions)}。")
        
        # 管理建议
        management_suggestions = [
            "建立定期的审核效果评估机制，每月生成详细的统计报告",
            "完善违规内容的分类处理流程，区分不同严重程度的违规行为",
            "加强审核人员的培训，确保审核标准的一致性和准确性",
            "建立跨部门的协调机制，及时处理发现的违规内容",
            "定期更新和维护违规检测规则库，适应新的违规形式",
            "建立应急响应机制，快速处理重大违规事件"
        ]
        
        conclusions.append(f"管理制度建议：{'; '.join(management_suggestions)}。")
        
        # 未来发展建议
        future_suggestions = [
            "探索人工智能技术在内容审核中的应用，提升自动化审核的准确性",
            "建立多模态内容审核能力，实现文本、图像、音频、视频的综合审核",
            "构建实时监控和预警系统，及时发现和处理违规内容",
            "建立行业内的审核标准和最佳实践分享机制",
            "研究和应用联邦学习等技术，在保护隐私的前提下提升审核效果"
        ]
        
        conclusions.append(f"未来发展建议：{'; '.join(future_suggestions)}。")
        
        return "\n\n".join(conclusions)
    
    def _generate_technical_notes(self) -> str:
        """生成技术说明"""
        technical_notes = """本报告基于内容审核统计分析系统生成，采用以下技术和方法：

数据来源：
• URL审核数据来自audit_results表，包含审核结果和违规原因
• 图片审核数据来自image_audit_results表，关联device_map表获取设备和位置信息
• 多媒体审核数据来自review_tasks、review_files和review_results三张关联表

违规类型识别：
• 采用基于正则表达式的模式匹配技术
• 支持10大类违规类型：涉黄、涉政、涉恐、恶意辱骂、虚假诈骗、广告推广、违禁词、舆情极端、黑名单词、地图问题
• 结合关键词匹配和语义分析提升识别准确性

统计分析方法：
• 使用时间序列分析识别趋势变化
• 采用多维度统计（时间、位置、设备、类型）
• 计算违规率、成功率等关键性能指标

数据可视化：
• 使用matplotlib和plotly生成多种类型的统计图表
• 支持饼图、柱状图、折线图、热力图等可视化形式
• 提供交互式仪表板展示

报告生成：
• 支持Excel、CSV、PDF三种格式的报告导出
• PDF报告包含完整的统计表格、图表和分析建议
• 采用reportlab库生成专业的PDF文档

数据质量保证：
• 实施严格的数据验证和清洗流程
• 采用异常值检测和处理机制
• 建立数据一致性检查和修复机制

系统性能：
• 采用数据库连接池优化查询性能
• 实施批量数据处理提升处理效率
• 使用异步编程模式提升系统响应速度

注意事项：
• 统计结果基于现有数据，可能存在滞后性
• 违规检测基于预定义规则，可能需要根据实际情况调整
• 建议结合人工审核验证自动检测结果的准确性
• 定期更新检测规则和算法以适应新的违规形式"""
        
        return technical_notes
    
    def export_all_formats(self, stats_data: Dict[str, Any], chart_files: List[str] = None, prefix: str = "") -> Dict[str, str]:
        """导出所有格式的报告
        
        Args:
            stats_data: 统计数据
            chart_files: 图表文件路径列表
            prefix: 文件名前缀
            
        Returns:
            各格式文件路径字典
        """
        logger.info("开始导出所有格式的报告")
        
        exported_files = {}
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # 导出Excel报告
            excel_filename = f"{prefix}audit_report_{timestamp}.xlsx"
            excel_path = self.export_excel_report(stats_data, excel_filename)
            exported_files['excel'] = excel_path
            logger.info(f"✓ Excel报告导出成功: {excel_path}")
            
            # 导出CSV报告
            csv_filename = f"{prefix}audit_summary_{timestamp}.csv"
            csv_path = self.export_csv_report(stats_data, csv_filename)
            exported_files['csv'] = csv_path
            logger.info(f"✓ CSV报告导出成功: {csv_path}")
            
            # 导出PDF报告
            pdf_filename = f"{prefix}audit_report_{timestamp}.pdf"
            pdf_path = self.export_pdf_report(stats_data, chart_files, pdf_filename)
            exported_files['pdf'] = pdf_path
            logger.info(f"✓ PDF报告导出成功: {pdf_path}")
            
            # 计算文件大小
            total_size = 0
            for file_path in exported_files.values():
                try:
                    size = os.path.getsize(file_path)
                    total_size += size
                except:
                    pass
            
            logger.info(f"所有格式报告导出完成，共生成 {len(exported_files)} 个文件，总大小: {total_size/(1024*1024):.1f}MB")
            return exported_files
            
        except Exception as e:
            logger.error(f"导出报告失败: {e}")
            return exported_files
    
    def create_quick_summary_pdf(self, stats_data: Dict[str, Any], filename: str = None) -> str:
        """创建快速摘要PDF（单页）
        
        Args:
            stats_data: 统计数据
            filename: 输出文件名
            
        Returns:
            生成的文件路径
        """
        logger.info("开始生成快速摘要PDF")
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'audit_summary_{timestamp}.pdf'
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
            story = []
            
            # 标题
            story.append(Paragraph("内容审核系统 - 快速统计摘要", self.title_style))
            story.append(Spacer(1, 0.3*inch))
            
            # 生成时间
            story.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.normal_style))
            story.append(Spacer(1, 0.2*inch))
            
            # 关键指标
            if 'overview' in stats_data and 'summary' in stats_data['overview']:
                summary = stats_data['overview']['summary']
                
                kpi_text = f"""
                关键指标概览：
                • 总审核量：{summary.get('total_audits', 0):,} 次
                • 总违规数：{summary.get('total_violations', 0):,} 处
                • 整体违规率：{summary.get('overall_violation_rate', 0):.2%}
                • 主要审核类型：{summary.get('most_active_audit_type', '未知')}
                """
                story.append(Paragraph(kpi_text, self.normal_style))
                story.append(Spacer(1, 0.2*inch))
            
            # 各模块摘要
            if 'overview' in stats_data:
                overview = stats_data['overview']
                
                if 'url_audit' in overview:
                    url_data = overview['url_audit']
                    url_text = f"URL审核：处理 {url_data.get('total', 0):,} 条，违规率 {url_data.get('violation_rate', 0):.2%}"
                    story.append(Paragraph(f"• {url_text}", self.normal_style))
                
                if 'image_audit' in overview:
                    image_data = overview['image_audit']
                    image_text = f"图片审核：处理 {image_data.get('total', 0):,} 张，违规率 {image_data.get('violation_rate', 0):.2%}，覆盖 {image_data.get('device_count', 0)} 台设备"
                    story.append(Paragraph(f"• {image_text}", self.normal_style))
                
                if 'multimedia_audit' in overview:
                    multimedia_data = overview['multimedia_audit']
                    multimedia_text = f"多媒体审核：处理 {multimedia_data.get('total_tasks', 0):,} 个任务，完成率 {multimedia_data.get('completion_rate', 0):.2%}"
                    story.append(Paragraph(f"• {multimedia_text}", self.normal_style))
            
            story.append(Spacer(1, 0.3*inch))
            
            # 简要结论
            conclusion_text = "系统运行状态良好，建议持续监控和优化审核策略。"
            if 'overview' in stats_data and 'summary' in stats_data['overview']:
                overall_rate = stats_data['overview']['summary'].get('overall_violation_rate', 0)
                if overall_rate > 0.1:
                    conclusion_text = "检测到较高违规率，建议加强审核策略和监管措施。"
                elif overall_rate < 0.03:
                    conclusion_text = "系统表现优秀，违规率控制良好，建议保持现有策略。"
            
            story.append(Paragraph(f"结论：{conclusion_text}", self.normal_style))
            
            # 构建PDF
            doc.build(story)
            
            logger.info(f"快速摘要PDF生成完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成快速摘要PDF失败: {e}")
            raise

def create_exporter(output_dir: str = None) -> ReportExporter:
    """创建报告导出器实例"""
    return ReportExporter(output_dir)


