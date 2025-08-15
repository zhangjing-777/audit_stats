
"""
数据可视化模块
负责生成各类统计图表和可视化报告
"""

import os
import logging
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config import OUTPUT_CONFIG, VISUALIZATION_CONFIG

logger = logging.getLogger(__name__)

class DataVisualizer:
    """数据可视化器"""
    
    def __init__(self, output_dir: str = None):
        """初始化可视化器
        
        Args:
            output_dir: 输出目录，默认使用配置中的目录
        """
        self.output_dir = output_dir or OUTPUT_CONFIG['visualization_dir']
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 设置matplotlib中文字体
        self._setup_matplotlib()
        
        # 设置seaborn样式
        sns.set_style("whitegrid")
        sns.set_palette("husl")
        
        logger.info(f"数据可视化器初始化完成，输出目录: {self.output_dir}")
    
    def _setup_matplotlib(self):
        """设置matplotlib中文字体"""
        try:
            plt.rcParams['font.sans-serif'] = VISUALIZATION_CONFIG['font_config']['family']
            plt.rcParams['axes.unicode_minus'] = False
            plt.rcParams['font.size'] = VISUALIZATION_CONFIG['font_config']['size']
            
            # 设置图形大小和DPI
            plt.rcParams['figure.figsize'] = VISUALIZATION_CONFIG['figure_size']
            plt.rcParams['savefig.dpi'] = VISUALIZATION_CONFIG['dpi']
            
            logger.debug("matplotlib中文字体设置完成")
        except Exception as e:
            logger.warning(f"matplotlib字体设置失败: {e}")
    
    def generate_overview_charts(self, stats_data: Dict[str, Any], filename: str = None) -> str:
        """生成整体概览图表
        
        Args:
            stats_data: 统计数据
            filename: 输出文件名
            
        Returns:
            生成的图片文件路径
        """
        logger.info("开始生成整体概览图表")
        
        if not filename:
            filename = f"overview_charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # 创建2x2的子图布局
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('内容审核系统整体概览', fontsize=16, fontweight='bold')
        
        try:
            if 'overview' in stats_data:
                overview = stats_data['overview']
                
                # 1. URL审核饼图
                self._draw_audit_pie_chart(axes[0, 0], overview.get('url_audit', {}), 'URL审核结果分布')
                
                # 2. 图片审核饼图
                self._draw_audit_pie_chart(axes[0, 1], overview.get('image_audit', {}), '图片审核结果分布')
                
                # 3. 多媒体任务状态饼图
                self._draw_multimedia_pie_chart(axes[1, 0], overview.get('multimedia_audit', {}), '多媒体任务状态分布')
                
                # 4. 总体违规率对比
                self._draw_violation_comparison(axes[1, 1], overview)
            
            plt.tight_layout()
            plt.savefig(filepath, bbox_inches='tight', facecolor='white')
            plt.close()
            
            logger.info(f"整体概览图表生成完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成整体概览图表失败: {e}")
            plt.close()
            raise
    
    def _draw_audit_pie_chart(self, ax, audit_data: Dict, title: str):
        """绘制审核结果饼图"""
        if not audit_data or audit_data.get('total', 0) == 0:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(title)
            return
        
        total = audit_data['total']
        violations = audit_data.get('violations', 0)
        compliant = total - violations
        
        if total > 0:
            labels = ['合规', '违规']
            sizes = [compliant, violations]
            colors = ['#2ca02c', '#d62728']
            
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                            colors=colors, startangle=90)
            
            # 设置文字样式
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
        
        ax.set_title(f'{title}\n(总数: {total:,})', fontsize=12, fontweight='bold')
    
    def _draw_multimedia_pie_chart(self, ax, multimedia_data: Dict, title: str):
        """绘制多媒体任务状态饼图"""
        if not multimedia_data or multimedia_data.get('total_tasks', 0) == 0:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title(title)
            return
        
        total_tasks = multimedia_data['total_tasks']
        completed = multimedia_data.get('completed_tasks', 0)
        pending = multimedia_data.get('pending_tasks', 0)
        failed = multimedia_data.get('failed_tasks', 0)
        processing = total_tasks - completed - pending - failed
        
        labels = ['已完成', '处理中', '待处理', '失败']
        sizes = [completed, processing, pending, failed]
        colors = ['#2ca02c', '#ff7f0e', '#1f77b4', '#d62728']
        
        # 过滤掉值为0的项
        filtered_data = [(label, size, color) for label, size, color in zip(labels, sizes, colors) if size > 0]
        
        if filtered_data:
            labels, sizes, colors = zip(*filtered_data)
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                            colors=colors, startangle=90)
            
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
        
        ax.set_title(f'{title}\n(总任务数: {total_tasks:,})', fontsize=12, fontweight='bold')
    
    def _draw_violation_comparison(self, ax, overview: Dict):
        """绘制违规率对比图"""
        categories = []
        violation_rates = []
        totals = []
        
        if 'url_audit' in overview:
            url_data = overview['url_audit']
            if url_data.get('total', 0) > 0:
                categories.append('URL审核')
                violation_rates.append(url_data['violation_rate'])
                totals.append(url_data['total'])
        
        if 'image_audit' in overview:
            image_data = overview['image_audit']
            if image_data.get('total', 0) > 0:
                categories.append('图片审核')
                violation_rates.append(image_data['violation_rate'])
                totals.append(image_data['total'])
        
        if categories:
            bars = ax.bar(categories, [rate * 100 for rate in violation_rates], 
                         color=['#ff7f0e', '#1f77b4'], alpha=0.8)
            
            # 添加数值标签
            for bar, rate, total in zip(bars, violation_rates, totals):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                       f'{rate:.1%}\n({total:,}条)', ha='center', va='bottom', fontsize=10)
            
            ax.set_ylabel('违规率 (%)')
            ax.set_title('各类审核违规率对比', fontsize=12, fontweight='bold')
            ax.set_ylim(0, max(violation_rates) * 120 if violation_rates else 100)
        else:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title('各类审核违规率对比')
    
    def generate_violation_types_chart(self, violation_data: Dict[str, int], filename: str = None) -> str:
        """生成违规类型分布图表
        
        Args:
            violation_data: 违规类型统计数据
            filename: 输出文件名
            
        Returns:
            生成的图片文件路径
        """
        logger.info("开始生成违规类型分布图表")
        
        if not filename:
            filename = f"violation_types_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filepath = os.path.join(self.output_dir, filename)
        
        if not violation_data:
            logger.warning("违规类型数据为空，跳过图表生成")
            return ""
        
        try:
            plt.figure(figsize=(14, 8))
            
            # 排序并选择前10个
            sorted_violations = sorted(violation_data.items(), key=lambda x: x[1], reverse=True)[:10]
            types, counts = zip(*sorted_violations) if sorted_violations else ([], [])
            
            # 创建颜色映射
            colors = plt.cm.Set3(np.linspace(0, 1, len(types)))
            
            bars = plt.bar(range(len(types)), counts, color=colors, alpha=0.8)
            
            # 添加数值标签
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{count}', ha='center', va='bottom', fontweight='bold')
            
            plt.title('违规类型分布统计', fontsize=16, fontweight='bold', pad=20)
            plt.xlabel('违规类型', fontsize=12)
            plt.ylabel('违规次数', fontsize=12)
            plt.xticks(range(len(types)), types, rotation=45, ha='right')
            plt.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(filepath, bbox_inches='tight', facecolor='white')
            plt.close()
            
            logger.info(f"违规类型分布图表生成完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成违规类型分布图表失败: {e}")
            plt.close()
            raise
    
    def generate_time_trend_chart(self, time_series: List[Dict], filename: str = None) -> str:
        """生成时间趋势图表
        
        Args:
            time_series: 时间序列数据
            filename: 输出文件名
            
        Returns:
            生成的图片文件路径
        """
        logger.info("开始生成时间趋势图表")
        
        if not filename:
            filename = f"time_trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filepath = os.path.join(self.output_dir, filename)
        
        if not time_series:
            logger.warning("时间序列数据为空，跳过图表生成")
            return ""
        
        try:
            # 转换数据
            df = pd.DataFrame(time_series)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
            
            # 上图：审核数量趋势
            ax1.plot(df['date'], df['daily_total'], 'b-', linewidth=2, marker='o', 
                    markersize=4, label='总审核数', alpha=0.8)
            ax1.plot(df['date'], df['daily_violations'], 'r-', linewidth=2, marker='s', 
                    markersize=4, label='违规数', alpha=0.8)
            
            ax1.set_title('审核数量时间趋势', fontsize=14, fontweight='bold')
            ax1.set_ylabel('审核数量', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 下图：违规率趋势
            if 'daily_violation_rate' in df.columns:
                violation_rates = df['daily_violation_rate'] * 100
            else:
                violation_rates = (df['daily_violations'] / df['daily_total'].replace(0, 1)) * 100
            
            ax2.plot(df['date'], violation_rates, 'g-', linewidth=2, marker='d', 
                    markersize=4, label='违规率', alpha=0.8)
            ax2.fill_between(df['date'], violation_rates, alpha=0.3, color='green')
            
            ax2.set_title('违规率时间趋势', fontsize=14, fontweight='bold')
            ax2.set_xlabel('日期', fontsize=12)
            ax2.set_ylabel('违规率 (%)', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # 设置日期格式
            for ax in [ax1, ax2]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(df) // 10)))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            plt.savefig(filepath, bbox_inches='tight', facecolor='white')
            plt.close()
            
            logger.info(f"时间趋势图表生成完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成时间趋势图表失败: {e}")
            plt.close()
            raise
    
    def generate_device_heatmap(self, location_stats: Dict, filename: str = None) -> str:
        """生成设备位置热力图
        
        Args:
            location_stats: 位置统计数据
            filename: 输出文件名
            
        Returns:
            生成的图片文件路径
        """
        logger.info("开始生成设备位置热力图")
        
        if not filename:
            filename = f"device_heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filepath = os.path.join(self.output_dir, filename)
        
        if not location_stats:
            logger.warning("位置统计数据为空，跳过图表生成")
            return ""
        
        try:
            # 准备数据
            locations = list(location_stats.keys())
            metrics = ['总数', '违规数', '违规率(%)', '设备数']
            
            # 构建数据矩阵
            data_matrix = []
            for location in locations:
                stats = location_stats[location]
                row = [
                    stats.get('total', 0),
                    stats.get('violations', 0),
                    stats.get('violation_rate', 0) * 100,
                    stats.get('device_count', 0)
                ]
                data_matrix.append(row)
            
            # 创建热力图
            plt.figure(figsize=(12, max(6, len(locations) * 0.5)))
            
            # 标准化数据用于颜色映射
            df = pd.DataFrame(data_matrix, index=locations, columns=metrics)
            df_normalized = df.div(df.max(axis=0), axis=1).fillna(0)
            
            sns.heatmap(df_normalized, annot=df.values, fmt='.0f', cmap='YlOrRd',
                       cbar_kws={'label': '标准化值'}, square=False)
            
            plt.title('设备位置审核统计热力图', fontsize=14, fontweight='bold', pad=20)
            plt.xlabel('统计指标', fontsize=12)
            plt.ylabel('位置', fontsize=12)
            plt.xticks(rotation=0)
            plt.yticks(rotation=0)
            
            plt.tight_layout()
            plt.savefig(filepath, bbox_inches='tight', facecolor='white')
            plt.close()
            
            logger.info(f"设备位置热力图生成完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成设备位置热力图失败: {e}")
            plt.close()
            raise
    
    def generate_interactive_dashboard(self, stats_data: Dict[str, Any], filename: str = None) -> str:
        """生成交互式仪表板
        
        Args:
            stats_data: 统计数据
            filename: 输出文件名
            
        Returns:
            生成的HTML文件路径
        """
        logger.info("开始生成交互式仪表板")
        
        if not filename:
            filename = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # 创建子图布局
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=('审核总量', '违规类型分布', '时间趋势', '位置分布', '文件类型分布', '处理性能'),
                specs=[[{"type": "indicator"}, {"type": "bar"}],
                       [{"colspan": 2}, None],
                       [{"type": "pie"}, {"type": "scatter"}]]
            )
            
            # 1. 审核总量指示器
            if 'overview' in stats_data:
                overview = stats_data['overview']
                total_audits = overview.get('summary', {}).get('total_audits', 0)
                total_violations = overview.get('summary', {}).get('total_violations', 0)
                
                fig.add_trace(go.Indicator(
                    mode="number+delta",
                    value=total_audits,
                    title={"text": "总审核数"},
                    delta={'position': "top", 'reference': total_violations},
                    domain={'x': [0, 1], 'y': [0, 1]}
                ), row=1, col=1)
            
            # 2. 违规类型分布
            if 'url_audit' in stats_data and 'violation_types' in stats_data['url_audit']:
                violation_types = stats_data['url_audit']['violation_types']
                if violation_types:
                    types = list(violation_types.keys())[:10]
                    counts = list(violation_types.values())[:10]
                    
                    fig.add_trace(go.Bar(
                        x=types,
                        y=counts,
                        name="违规类型",
                        marker_color='lightcoral'
                    ), row=1, col=2)
            
            # 3. 时间趋势
            if 'url_audit' in stats_data and 'time_series' in stats_data['url_audit']:
                time_series = stats_data['url_audit']['time_series']
                if time_series:
                    dates = [item['date'] for item in time_series]
                    totals = [item['daily_total'] for item in time_series]
                    violations = [item['daily_violations'] for item in time_series]
                    
                    fig.add_trace(go.Scatter(
                        x=dates, y=totals,
                        mode='lines+markers',
                        name='总审核数',
                        line=dict(color='blue')
                    ), row=2, col=1)
                    
                    fig.add_trace(go.Scatter(
                        x=dates, y=violations,
                        mode='lines+markers',
                        name='违规数',
                        line=dict(color='red')
                    ), row=2, col=1)
            
            # 4. 位置分布饼图
            if 'image_audit' in stats_data and 'location_stats' in stats_data['image_audit']:
                location_stats = stats_data['image_audit']['location_stats']
                if location_stats:
                    locations = list(location_stats.keys())
                    totals = [stats['total'] for stats in location_stats.values()]
                    
                    fig.add_trace(go.Pie(
                        labels=locations,
                        values=totals,
                        name="位置分布"
                    ), row=3, col=1)
            
            # 5. 性能散点图
            if 'multimedia_audit' in stats_data:
                multimedia = stats_data['multimedia_audit']
                if 'file_stats' in multimedia and 'file_type_distribution' in multimedia['file_stats']:
                    file_types = multimedia['file_stats']['file_type_distribution']
                    if file_types:
                        x_vals = [item['count'] for item in file_types]
                        y_vals = [item['violations'] for item in file_types]
                        labels = [item['file_type'] for item in file_types]
                        
                        fig.add_trace(go.Scatter(
                            x=x_vals, y=y_vals,
                            mode='markers',
                            text=labels,
                            marker=dict(size=10, opacity=0.8),
                            name="文件类型性能"
                        ), row=3, col=2)
            
            # 更新布局
            fig.update_layout(
                title_text="内容审核系统仪表板",
                showlegend=True,
                height=900
            )
            
            # 保存为HTML
            fig.write_html(filepath)
            
            logger.info(f"交互式仪表板生成完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成交互式仪表板失败: {e}")
            raise
    
    def generate_all_visualizations(self, stats_data: Dict[str, Any], prefix: str = "") -> List[str]:
        """生成所有可视化图表
        
        Args:
            stats_data: 统计数据
            prefix: 文件名前缀
            
        Returns:
            生成的文件路径列表
        """
        logger.info("开始生成所有可视化图表")
        
        generated_files = []
        
        try:
            # 1. 整体概览图表
            overview_file = self.generate_overview_charts(stats_data, f"{prefix}overview.png")
            if overview_file:
                generated_files.append(overview_file)
            
            # 2. 违规类型分布图
            if 'url_audit' in stats_data and 'violation_types' in stats_data['url_audit']:
                violation_file = self.generate_violation_types_chart(
                    stats_data['url_audit']['violation_types'], 
                    f"{prefix}violation_types.png"
                )
                if violation_file:
                    generated_files.append(violation_file)
            
            # 3. 时间趋势图
            if 'url_audit' in stats_data and 'time_series' in stats_data['url_audit']:
                trend_file = self.generate_time_trend_chart(
                    stats_data['url_audit']['time_series'], 
                    f"{prefix}time_trend.png"
                )
                if trend_file:
                    generated_files.append(trend_file)
            
            # 4. 设备热力图
            if 'image_audit' in stats_data and 'location_stats' in stats_data['image_audit']:
                heatmap_file = self.generate_device_heatmap(
                    stats_data['image_audit']['location_stats'], 
                    f"{prefix}device_heatmap.png"
                )
                if heatmap_file:
                    generated_files.append(heatmap_file)
            
            # 5. 交互式仪表板
            dashboard_file = self.generate_interactive_dashboard(stats_data, f"{prefix}dashboard.html")
            if dashboard_file:
                generated_files.append(dashboard_file)
            
            logger.info(f"所有可视化图表生成完成，共生成 {len(generated_files)} 个文件")
            return generated_files
            
        except Exception as e:
            logger.error(f"生成可视化图表失败: {e}")
            return generated_files
    
    def create_summary_image(self, stats_data: Dict[str, Any], filename: str = None) -> str:
        """创建统计摘要图片
        
        Args:
            stats_data: 统计数据
            filename: 输出文件名
            
        Returns:
            生成的图片文件路径
        """
        logger.info("开始生成统计摘要图片")
        
        if not filename:
            filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.axis('off')
            
            # 添加标题
            fig.suptitle('内容审核系统统计摘要', fontsize=20, fontweight='bold', y=0.95)
            
            # 准备摘要数据
            summary_text = self._prepare_summary_text(stats_data)
            
            # 添加文本
            ax.text(0.05, 0.85, summary_text, transform=ax.transAxes, fontsize=12,
                   verticalalignment='top', bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
            
            # 添加生成时间
            generation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ax.text(0.95, 0.05, f'生成时间: {generation_time}', transform=ax.transAxes, 
                   fontsize=10, ha='right', va='bottom')
            
            plt.savefig(filepath, bbox_inches='tight', facecolor='white', dpi=300)
            plt.close()
            
            logger.info(f"统计摘要图片生成完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"生成统计摘要图片失败: {e}")
            plt.close()
            raise
    
    def _prepare_summary_text(self, stats_data: Dict[str, Any]) -> str:
        """准备摘要文本"""
        lines = []
        
        if 'overview' in stats_data:
            overview = stats_data['overview']
            
            # URL审核摘要
            if 'url_audit' in overview:
                url_data = overview['url_audit']
                lines.append(f"📊 URL审核:")
                lines.append(f"   • 总审核数: {url_data.get('total', 0):,} 条")
                lines.append(f"   • 违规数: {url_data.get('violations', 0):,} 条")
                lines.append(f"   • 违规率: {url_data.get('violation_rate', 0):.2%}")
                lines.append("")
            
            # 图片审核摘要
            if 'image_audit' in overview:
                image_data = overview['image_audit']
                lines.append(f"🖼️ 图片审核:")
                lines.append(f"   • 总审核数: {image_data.get('total', 0):,} 张")
                lines.append(f"   • 违规数: {image_data.get('violations', 0):,} 张")
                lines.append(f"   • 违规率: {image_data.get('violation_rate', 0):.2%}")
                lines.append(f"   • 覆盖设备: {image_data.get('device_count', 0)} 台")
                lines.append("")
            
            # 多媒体审核摘要
            if 'multimedia_audit' in overview:
                multimedia_data = overview['multimedia_audit']
                lines.append(f"🎬 多媒体审核:")
                lines.append(f"   • 总任务数: {multimedia_data.get('total_tasks', 0):,} 个")
                lines.append(f"   • 完成率: {multimedia_data.get('completion_rate', 0):.2%}")
                lines.append(f"   • 总文件数: {multimedia_data.get('total_files', 0):,} 个")
                lines.append(f"   • 发现违规: {multimedia_data.get('total_violations', 0):,} 处")
                lines.append("")
            
            # 系统总结
            if 'summary' in overview:
                summary = overview['summary']
                lines.append(f"📈 系统总结:")
                lines.append(f"   • 总审核量: {summary.get('total_audits', 0):,}")
                lines.append(f"   • 总违规数: {summary.get('total_violations', 0):,}")
                lines.append(f"   • 整体违规率: {summary.get('overall_violation_rate', 0):.2%}")
        
        return '\n'.join(lines)

def create_visualizer(output_dir: str = None) -> DataVisualizer:
    """创建数据可视化器实例"""
    return DataVisualizer(output_dir)