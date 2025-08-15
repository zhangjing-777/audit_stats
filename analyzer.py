
"""
审核统计分析器模块
负责各类审核数据的统计分析
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import time

from database import DatabaseManager, QueryBuilder
from reason_parser import ReasonParser


logger = logging.getLogger(__name__)

class AuditStatsAnalyzer:
    """审核统计分析器"""
    
    def __init__(self, db_manager: DatabaseManager):
        """初始化分析器
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager
        self.reason_parser = ReasonParser()
        logger.info("审核统计分析器初始化完成")
    
    def get_overview_stats(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """获取整体概览统计
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            整体概览统计数据
        """
        logger.info(f"开始获取整体概览统计，时间范围: {start_date} - {end_date}")
        start_time = time.time()
        
        try:
            # 构建时间过滤条件
            date_filter = ""
            params = []
            if start_date and end_date:
                date_filter = " WHERE created_at BETWEEN %s AND %s"
                params = [start_date, end_date]
            
            # URL审核统计
            url_stats = self._get_url_overview(date_filter, params)
            
            # 图片审核统计
            image_stats = self._get_image_overview(date_filter, params)
            
            # 多媒体审核统计
            multimedia_stats = self._get_multimedia_overview(date_filter, params)
            
            # 系统健康状态
            system_health = self._get_system_health()
            
            overview = {
                'url_audit': url_stats,
                'image_audit': image_stats,
                'multimedia_audit': multimedia_stats,
                'system_health': system_health,
                'summary': self._calculate_summary(url_stats, image_stats, multimedia_stats),
                'generated_at': datetime.now().isoformat()
            }
            
            execution_time = time.time() - start_time
            logger.info(f"整体概览统计完成，耗时: {execution_time:.2f}秒")
            
            return overview
            
        except Exception as e:
            logger.error(f"获取整体概览统计失败: {e}")
            raise
    
    def _get_url_overview(self, date_filter: str, params: List) -> Dict[str, Any]:
        """获取URL审核概览"""
        # 基础统计
        basic_query = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN verdict = '不合规' THEN 1 END) as violations,
            COUNT(CASE WHEN verdict = '合规' THEN 1 END) as compliant,
            COUNT(CASE WHEN verdict = '不确定' THEN 1 END) as uncertain
        FROM audit_results
        {date_filter}
        """
        basic_result = self.db.execute_query(basic_query, params, fetch_one=True)
        basic_stats = basic_result[0] if basic_result else {}
        
        # 时间趋势
        trend_query = f"""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as daily_total,
            COUNT(CASE WHEN verdict = '不合规' THEN 1 END) as daily_violations
        FROM audit_results
        {date_filter}
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
        """
        trend_stats = self.db.execute_query(trend_query, params)
        
        return {
            'total': basic_stats.get('total', 0),
            'violations': basic_stats.get('violations', 0),
            'compliant': basic_stats.get('compliant', 0),
            'uncertain': basic_stats.get('uncertain', 0),
            'violation_rate': basic_stats.get('violations', 0) / max(basic_stats.get('total', 1), 1),
            'daily_stats': trend_stats
        }
    
    def _get_image_overview(self, date_filter: str, params: List) -> Dict[str, Any]:
        """获取图片审核概览"""
        # 基础统计
        basic_query = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN audit_result = '不合规' THEN 1 END) as violations,
            COUNT(CASE WHEN audit_result = '合规' THEN 1 END) as compliant,
            COUNT(CASE WHEN audit_result = '审核失败' THEN 1 END) as failed
        FROM image_audit_results
        {date_filter}
        """
        basic_result = self.db.execute_query(basic_query, params, fetch_one=True)
        basic_stats = basic_result[0] if basic_result else {}
        
        # 设备统计
        device_query = f"""
        SELECT 
            COUNT(DISTINCT iar.mac_address) as device_count,
            COUNT(DISTINCT dm.location) as location_count
        FROM image_audit_results iar
        LEFT JOIN device_map dm ON iar.mac_address = dm.mac_address
        {date_filter}
        """
        device_result = self.db.execute_query(device_query, params, fetch_one=True)
        device_stats = device_result[0] if device_result else {}
        
        return {
            'total': basic_stats.get('total', 0),
            'violations': basic_stats.get('violations', 0),
            'compliant': basic_stats.get('compliant', 0),
            'failed': basic_stats.get('failed', 0),
            'violation_rate': basic_stats.get('violations', 0) / max(basic_stats.get('total', 1), 1),
            'device_count': device_stats.get('device_count', 0),
            'location_count': device_stats.get('location_count', 0)
        }
    
    def _get_multimedia_overview(self, date_filter: str, params: List) -> Dict[str, Any]:
        """获取多媒体审核概览"""
        # 任务统计
        task_query = f"""
        SELECT 
            COUNT(*) as total_tasks,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
            SUM(violation_count) as total_violations,
            AVG(progress) as avg_progress
        FROM review_tasks
        {date_filter}
        """
        task_result = self.db.execute_query(task_query, params, fetch_one=True)
        task_stats = task_result[0] if task_result else {}
        
        # 文件统计
        file_query = f"""
        SELECT 
            COUNT(*) as total_files,
            SUM(file_size) as total_size,
            COUNT(DISTINCT file_type) as file_types
        FROM review_files rf
        JOIN review_tasks rt ON rf.task_id = rt.id
        {date_filter}
        """
        file_result = self.db.execute_query(file_query, params, fetch_one=True)
        file_stats = file_result[0] if file_result else {}
        
        return {
            'total_tasks': task_stats.get('total_tasks', 0),
            'completed_tasks': task_stats.get('completed', 0),
            'pending_tasks': task_stats.get('pending', 0),
            'failed_tasks': task_stats.get('failed', 0),
            'total_violations': task_stats.get('total_violations', 0),
            'avg_progress': task_stats.get('avg_progress', 0),
            'total_files': file_stats.get('total_files', 0),
            'total_size': file_stats.get('total_size', 0),
            'file_types': file_stats.get('file_types', 0),
            'completion_rate': task_stats.get('completed', 0) / max(task_stats.get('total_tasks', 1), 1)
        }
    
    def _get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        today = datetime.now().date()
        
        # 今日审核量
        today_audits_query = """
        SELECT 
            (SELECT COUNT(*) FROM audit_results WHERE DATE(created_at) = %s) as url_audits,
            (SELECT COUNT(*) FROM image_audit_results WHERE DATE(created_at) = %s) as image_audits,
            (SELECT COUNT(*) FROM review_tasks WHERE DATE(created_at) = %s) as multimedia_tasks
        """
        today_result = self.db.execute_query(today_audits_query, (today, today, today), fetch_one=True)
        today_stats = today_result[0] if today_result else {}
        
        # 活跃设备数
        active_devices_query = """
        SELECT COUNT(DISTINCT mac_address) as active_devices
        FROM image_audit_results 
        WHERE created_at >= %s
        """
        yesterday = today - timedelta(days=1)
        active_result = self.db.execute_query(active_devices_query, (yesterday,), fetch_one=True)
        active_devices = active_result[0]['active_devices'] if active_result else 0
        
        # 错误率统计
        error_rate_query = """
        SELECT 
            (SELECT COUNT(*) FROM image_audit_results WHERE audit_result = '审核失败' AND DATE(created_at) = %s) as image_errors,
            (SELECT COUNT(*) FROM review_tasks WHERE status = 'failed' AND DATE(created_at) = %s) as task_errors
        """
        error_result = self.db.execute_query(error_rate_query, (today, today), fetch_one=True)
        error_stats = error_result[0] if error_result else {}
        
        total_today = today_stats.get('url_audits', 0) + today_stats.get('image_audits', 0)
        total_errors = error_stats.get('image_errors', 0) + error_stats.get('task_errors', 0)
        
        return {
            'audits_today': total_today,
            'violations_today': 0,  # 需要进一步计算
            'active_devices': active_devices,
            'error_rate': total_errors / max(total_today, 1),
            'pending_tasks': 0,  # 从多媒体统计中获取
            'system_uptime': 1.0,  # 简化处理
            'last_updated': datetime.now().isoformat()
        }
    
    def _calculate_summary(self, url_stats: Dict, image_stats: Dict, multimedia_stats: Dict) -> Dict[str, Any]:
        """计算汇总信息"""
        total_audits = url_stats['total'] + image_stats['total']
        total_violations = url_stats['violations'] + image_stats['violations'] + multimedia_stats['total_violations']
        
        return {
            'total_audits': total_audits,
            'total_violations': total_violations,
            'overall_violation_rate': total_violations / max(total_audits, 1),
            'url_percentage': url_stats['total'] / max(total_audits, 1),
            'image_percentage': image_stats['total'] / max(total_audits, 1),
            'most_active_audit_type': 'url' if url_stats['total'] > image_stats['total'] else 'image'
        }
    
    def get_url_audit_stats(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """获取URL审核详细统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            URL审核统计数据
        """
        logger.info(f"开始获取URL审核统计，时间范围: {start_date} - {end_date}")
        start_time = time.time()
        
        try:
            # 构建查询条件
            builder = QueryBuilder()
            builder.select("*").from_table("audit_results")
            
            if start_date and end_date:
                builder.where_between("created_at", start_date, end_date)
            
            query, params = builder.build()
            audit_records = self.db.execute_query(query, params)
            
            # 基础统计
            total_count = len(audit_records)
            violation_records = [r for r in audit_records if r['verdict'] == '不合规']
            violation_count = len(violation_records)
            
            # 解析违规类型
            violation_types = defaultdict(int)
            violation_reasons = defaultdict(list)
            
            for record in violation_records:
                if record['reason']:
                    violations = self.reason_parser.parse_reason(record['reason'])
                    for violation in violations:
                        violation_types[violation] += 1
                        violation_reasons[violation].append(record['reason'][:100])
            
            # 时间趋势分析
            time_series = self._calculate_time_series(audit_records, 'created_at', 'verdict')
            
            # TOP违规原因
            top_reasons = self._get_top_violation_reasons(violation_records)
            
            result = {
                'total_count': total_count,
                'violation_count': violation_count,
                'violation_rate': violation_count / max(total_count, 1),
                'violation_types': dict(violation_types),
                'top_violation_reasons': top_reasons,
                'time_series': time_series,
                'processing_metrics': self._calculate_processing_metrics(audit_records),
                'quality_metrics': self._estimate_quality_metrics(audit_records)
            }
            
            execution_time = time.time() - start_time
            logger.info(f"URL审核统计完成，总数: {total_count}, 违规数: {violation_count}, 耗时: {execution_time:.2f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"获取URL审核统计失败: {e}")
            raise
    
    def get_image_audit_stats(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """获取图片审核详细统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            图片审核统计数据
        """
        logger.info(f"开始获取图片审核统计，时间范围: {start_date} - {end_date}")
        start_time = time.time()
        
        try:
            # 关联查询图片审核和设备信息
            date_filter = ""
            params = []
            if start_date and end_date:
                date_filter = " AND iar.created_at BETWEEN %s AND %s"
                params = [start_date, end_date]
            
            query = f"""
            SELECT 
                iar.*,
                dm.location,
                dm.device_id,
                dm.status as device_status
            FROM image_audit_results iar
            LEFT JOIN device_map dm ON iar.mac_address = dm.mac_address
            WHERE 1=1 {date_filter}
            ORDER BY iar.created_at DESC
            """
            
            image_records = self.db.execute_query(query, params)
            
            # 基础统计
            total_count = len(image_records)
            violation_records = [r for r in image_records if r['audit_result'] == '不合规']
            violation_count = len(violation_records)
            
            # 位置统计
            location_stats = self._calculate_location_stats(image_records)
            
            # 设备统计
            device_stats = self._calculate_device_stats(image_records)
            
            # 违规类型分析
            violation_types = defaultdict(int)
            for record in violation_records:
                if record['reasons']:
                    violations = self.reason_parser.parse_reason(record['reasons'])
                    for violation in violations:
                        violation_types[violation] += 1
            
            # 时间趋势
            time_series = self._calculate_time_series(image_records, 'created_at', 'audit_result')
            
            result = {
                'total_count': total_count,
                'violation_count': violation_count,
                'violation_rate': violation_count / max(total_count, 1),
                'location_stats': location_stats,
                'device_stats': device_stats,
                'violation_types': dict(violation_types),
                'time_series': time_series,
                'failed_count': len([r for r in image_records if r['audit_result'] == '审核失败']),
                'success_rate': (total_count - len([r for r in image_records if r['audit_result'] == '审核失败'])) / max(total_count, 1)
            }
            
            execution_time = time.time() - start_time
            logger.info(f"图片审核统计完成，总数: {total_count}, 违规数: {violation_count}, 耗时: {execution_time:.2f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"获取图片审核统计失败: {e}")
            raise
    
    def get_multimedia_audit_stats(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """获取多媒体审核详细统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            多媒体审核统计数据
        """
        logger.info(f"开始获取多媒体审核统计，时间范围: {start_date} - {end_date}")
        start_time = time.time()
        
        try:
            date_filter = ""
            params = []
            if start_date and end_date:
                date_filter = " WHERE rt.created_at BETWEEN %s AND %s"
                params = [start_date, end_date]
            
            # 任务级别统计
            task_stats = self._get_task_level_stats(date_filter, params)
            
            # 文件级别统计
            file_stats = self._get_file_level_stats(date_filter, params)
            
            # 审核结果统计
            result_stats = self._get_result_level_stats(date_filter, params)
            
            # 性能指标
            processing_metrics = self._get_multimedia_processing_metrics(date_filter, params)
            
            result = {
                'task_stats': task_stats,
                'file_stats': file_stats,
                'result_stats': result_stats,
                'processing_metrics': processing_metrics,
                'summary': {
                    'total_tasks': task_stats.get('total_tasks', 0),
                    'total_files': file_stats.get('total_files', 0),
                    'total_violations': result_stats.get('total_violations', 0),
                    'avg_files_per_task': file_stats.get('total_files', 0) / max(task_stats.get('total_tasks', 1), 1),
                    'avg_violations_per_file': result_stats.get('total_violations', 0) / max(file_stats.get('total_files', 1), 1)
                }
            }
            
            execution_time = time.time() - start_time
            logger.info(f"多媒体审核统计完成，任务数: {task_stats.get('total_tasks', 0)}, 耗时: {execution_time:.2f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"获取多媒体审核统计失败: {e}")
            raise
    
    def _calculate_time_series(self, records: List[Dict], date_field: str, status_field: str) -> List[Dict]:
        """计算时间序列数据"""
        daily_stats = defaultdict(lambda: {'total': 0, 'violations': 0})
        
        for record in records:
            if record[date_field]:
                date = record[date_field].date() if hasattr(record[date_field], 'date') else record[date_field]
                daily_stats[date]['total'] += 1
                
                if record[status_field] in ['不合规']:
                    daily_stats[date]['violations'] += 1
        
        # 转换为列表格式
        time_series = []
        for date in sorted(daily_stats.keys()):
            stats = daily_stats[date]
            time_series.append({
                'date': date.isoformat() if hasattr(date, 'isoformat') else str(date),
                'daily_total': stats['total'],
                'daily_violations': stats['violations'],
                'daily_violation_rate': stats['violations'] / max(stats['total'], 1)
            })
        
        return time_series
    
    def _calculate_location_stats(self, records: List[Dict]) -> Dict[str, Dict]:
        """计算位置统计"""
        location_data = defaultdict(lambda: {'total': 0, 'violations': 0, 'devices': set()})
        
        for record in records:
            location = record.get('location') or '未知位置'
            location_data[location]['total'] += 1
            location_data[location]['devices'].add(record['mac_address'])
            
            if record['audit_result'] == '不合规':
                location_data[location]['violations'] += 1
        
        # 转换为最终格式
        result = {}
        for location, data in location_data.items():
            result[location] = {
                'total': data['total'],
                'violations': data['violations'],
                'violation_rate': data['violations'] / max(data['total'], 1),
                'device_count': len(data['devices'])
            }
        
        return result
    
    def _calculate_device_stats(self, records: List[Dict]) -> Dict[str, Dict]:
        """计算设备统计"""
        device_data = defaultdict(lambda: {'total': 0, 'violations': 0, 'location': '', 'ip': '', 'status': ''})
        
        for record in records:
            device_id = record.get('device_id') or f"未知设备_{record['mac_address'][-6:]}"
            device_data[device_id]['total'] += 1
            device_data[device_id]['location'] = record.get('location', '未知位置')
            device_data[device_id]['ip'] = record['ip_address']
            device_data[device_id]['status'] = record.get('device_status', '未知')
            
            if record['audit_result'] == '不合规':
                device_data[device_id]['violations'] += 1
        
        # 转换为最终格式
        result = {}
        for device_id, data in device_data.items():
            result[device_id] = {
                'total': data['total'],
                'violations': data['violations'],
                'violation_rate': data['violations'] / max(data['total'], 1),
                'location': data['location'],
                'ip_address': data['ip'],
                'status': data['status']
            }
        
        return result
    
    def _get_top_violation_reasons(self, violation_records: List[Dict], top_n: int = 10) -> List[Dict]:
        """获取TOP违规原因"""
        reason_counter = defaultdict(int)
        reason_examples = defaultdict(list)
        
        for record in violation_records:
            if record['reason']:
                # 提取关键短语作为原因分类
                reason_key = record['reason'][:50] + "..." if len(record['reason']) > 50 else record['reason']
                reason_counter[reason_key] += 1
                
                if len(reason_examples[reason_key]) < 3:
                    reason_examples[reason_key].append(record['url'])
        
        # 排序并返回TOP N
        top_reasons = []
        for reason, count in sorted(reason_counter.items(), key=lambda x: x[1], reverse=True)[:top_n]:
            top_reasons.append({
                'reason': reason,
                'count': count,
                'percentage': count / len(violation_records),
                'examples': reason_examples[reason]
            })
        
        return top_reasons
    
    def _calculate_processing_metrics(self, records: List[Dict]) -> Dict[str, float]:
        """计算处理性能指标"""
        if not records:
            return {'avg_processing_time': 0, 'throughput': 0, 'success_rate': 0}
        
        # 简化的性能指标计算
        success_count = len([r for r in records if r['verdict'] in ['合规', '不合规']])
        
        return {
            'avg_processing_time': 0.5,  # 模拟平均处理时间
            'throughput': len(records),  # 处理量
            'success_rate': success_count / len(records),
            'error_rate': 1 - (success_count / len(records))
        }
    
    def _estimate_quality_metrics(self, records: List[Dict]) -> Dict[str, float]:
        """估算质量指标"""
        # 简化的质量指标估算
        total = len(records)
        if total == 0:
            return {'accuracy': 0, 'precision': 0, 'recall': 0}
        
        violations = len([r for r in records if r['verdict'] == '不合规'])
        
        return {
            'accuracy': 0.95,  # 模拟准确率
            'precision': 0.90,  # 模拟精确率
            'recall': 0.85,    # 模拟召回率
            'violation_ratio': violations / total
        }
    
    def _get_task_level_stats(self, date_filter: str, params: List) -> Dict[str, Any]:
        """获取任务级别统计"""
        query = f"""
        SELECT 
            COUNT(*) as total_tasks,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
            SUM(violation_count) as total_violations,
            AVG(progress) as avg_progress,
            AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration
        FROM review_tasks rt
        {date_filter}
        """
        
        result = self.db.execute_query(query, params, fetch_one=True)
        return result[0] if result else {}
    
    def _get_file_level_stats(self, date_filter: str, params: List) -> Dict[str, Any]:
        """获取文件级别统计"""
        query = f"""
        SELECT 
            COUNT(*) as total_files,
            COUNT(DISTINCT file_type) as file_types,
            SUM(file_size) as total_size,
            AVG(file_size) as avg_size,
            SUM(violation_count) as total_violations,
            SUM(ocr_blocks_count) as total_ocr_blocks,
            SUM(text_blocks_count) as total_text_blocks,
            SUM(image_blocks_count) as total_image_blocks
        FROM review_files rf
        JOIN review_tasks rt ON rf.task_id = rt.id
        {date_filter}
        """
        
        result = self.db.execute_query(query, params, fetch_one=True)
        stats = result[0] if result else {}
        
        # 文件类型分布
        type_query = f"""
        SELECT 
            file_type,
            COUNT(*) as count,
            SUM(file_size) as total_size,
            SUM(violation_count) as violations
        FROM review_files rf
        JOIN review_tasks rt ON rf.task_id = rt.id
        {date_filter}
        GROUP BY file_type
        ORDER BY count DESC
        """
        
        type_stats = self.db.execute_query(type_query, params)
        stats['file_type_distribution'] = type_stats
        
        return stats
    
    def _get_result_level_stats(self, date_filter: str, params: List) -> Dict[str, Any]:
        """获取审核结果级别统计"""
        query = f"""
        SELECT 
            COUNT(*) as total_results,
            COUNT(DISTINCT violation_type) as violation_types,
            COUNT(DISTINCT source_type) as source_types,
            AVG(confidence_score) as avg_confidence,
            COUNT(CASE WHEN is_reviewed = true THEN 1 END) as reviewed_count
        FROM review_results rr
        JOIN review_files rf ON rr.file_id = rf.id
        JOIN review_tasks rt ON rf.task_id = rt.id
        {date_filter}
        """
        
        result = self.db.execute_query(query, params, fetch_one=True)
        stats = result[0] if result else {}
        
        # 违规类型分布
        violation_query = f"""
        SELECT 
            violation_type,
            COUNT(*) as count,
            AVG(confidence_score) as avg_confidence
        FROM review_results rr
        JOIN review_files rf ON rr.file_id = rf.id
        JOIN review_tasks rt ON rf.task_id = rt.id
        {date_filter}
        GROUP BY violation_type
        ORDER BY count DESC
        """
        
        violation_stats = self.db.execute_query(violation_query, params)
        stats['violation_distribution'] = violation_stats
        
        return stats
    
    def _get_multimedia_processing_metrics(self, date_filter: str, params: List) -> Dict[str, Any]:
        """获取多媒体处理性能指标"""
        query = f"""
        SELECT 
            AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_task_duration,
            MAX(EXTRACT(EPOCH FROM (completed_at - started_at))) as max_task_duration,
            MIN(EXTRACT(EPOCH FROM (completed_at - started_at))) as min_task_duration,
            COUNT(CASE WHEN status = 'completed' THEN 1 END)::float / COUNT(*) as success_rate
        FROM review_tasks rt
        {date_filter}
        AND completed_at IS NOT NULL
        AND started_at IS NOT NULL
        """
        
        result = self.db.execute_query(query, params, fetch_one=True)
        return result[0] if result else {}

def create_analyzer(db_manager: DatabaseManager) -> AuditStatsAnalyzer:
    """创建审核统计分析器实例"""
    return AuditStatsAnalyzer(db_manager)