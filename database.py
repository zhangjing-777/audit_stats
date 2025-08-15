#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理模块 - 精简版
只保留实际需要的功能
"""

import logging
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import time

from config import DATABASE_CONFIG

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """数据库操作异常"""
    pass

class DatabaseManager:
    """数据库连接管理器 - 精简版"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化数据库管理器
        
        Args:
            config: 数据库配置字典，如果为None则使用默认配置
        """
        self.config = config or DATABASE_CONFIG
        self.pool = None
        self._init_pool()
        logger.info("数据库连接池初始化完成")
    
    def _init_pool(self):
        """初始化连接池"""
        try:
            self.pool = SimpleConnectionPool(
                minconn=self.config.get('minconn', 1),
                maxconn=self.config.get('maxconn', 10),
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            logger.info(f"连接池创建成功: {self.config['host']}:{self.config['port']}/{self.config['database']}")
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            raise DatabaseError(f"无法连接到数据库: {e}")
    
    def get_connection(self):
        """获取数据库连接"""
        if not self.pool:
            raise DatabaseError("连接池未初始化")
        return self.pool.getconn()
    
    def return_connection(self, conn):
        """归还数据库连接"""
        if self.pool and conn:
            self.pool.putconn(conn)
    
    @contextmanager
    def get_connection_context(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False) -> List[Dict]:
        """执行查询并返回结果
        
        Args:
            query: SQL查询语句
            params: 查询参数
            fetch_one: 是否只返回一条记录
            
        Returns:
            查询结果列表
        """
        start_time = time.time()
        
        with self.get_connection_context() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, params)
                    
                    if fetch_one:
                        result = cur.fetchone()
                        return [dict(result)] if result else []
                    else:
                        return [dict(row) for row in cur.fetchall()]
                        
            except Exception as e:
                logger.error(f"查询执行失败: {query[:100]}..., 参数: {params}, 错误: {e}")
                raise DatabaseError(f"查询执行失败: {e}")
            finally:
                execution_time = time.time() - start_time
                logger.debug(f"查询执行时间: {execution_time:.3f}秒")
    
    def execute_batch(self, operations: List[tuple]) -> None:
        """批量执行操作
        
        Args:
            operations: 操作列表，每个元素是(query, params)元组
        """
        with self.get_connection_context() as conn:
            try:
                with conn.cursor() as cur:
                    for query, params in operations:
                        cur.execute(query, params)
                    conn.commit()
                    logger.debug(f"批量操作成功，执行了 {len(operations)} 个操作")
            except Exception as e:
                logger.error(f"批量操作失败: {e}")
                raise DatabaseError(f"批量操作失败: {e}")
    
    def check_connection(self) -> bool:
        """检查数据库连接状态
        
        Returns:
            连接是否正常
        """
        try:
            result = self.execute_query("SELECT 1", fetch_one=True)
            return len(result) > 0
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return False
    
    def close(self):
        """关闭连接池"""
        if self.pool:
            self.pool.closeall()
            self.pool = None
            logger.info("数据库连接池已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class QueryBuilder:
    """SQL查询构建器"""
    
    def __init__(self):
        """初始化查询构建器"""
        self._select_fields = []
        self._from_table = ""
        self._where_conditions = []
        self._order_by = []
        self._limit = None
        self._params = []
    
    def select(self, fields: str) -> 'QueryBuilder':
        """设置SELECT字段
        
        Args:
            fields: 选择的字段，如 "*" 或 "field1, field2"
            
        Returns:
            QueryBuilder实例，支持链式调用
        """
        self._select_fields.append(fields)
        return self
    
    def from_table(self, table: str) -> 'QueryBuilder':
        """设置FROM表名
        
        Args:
            table: 表名
            
        Returns:
            QueryBuilder实例，支持链式调用
        """
        self._from_table = table
        return self
    
    def where(self, condition: str, *params) -> 'QueryBuilder':
        """添加WHERE条件
        
        Args:
            condition: WHERE条件
            *params: 参数
            
        Returns:
            QueryBuilder实例，支持链式调用
        """
        self._where_conditions.append(condition)
        self._params.extend(params)
        return self
    
    def where_between(self, field: str, start_value, end_value) -> 'QueryBuilder':
        """添加BETWEEN条件
        
        Args:
            field: 字段名
            start_value: 开始值
            end_value: 结束值
            
        Returns:
            QueryBuilder实例，支持链式调用
        """
        condition = f"{field} BETWEEN %s AND %s"
        self._where_conditions.append(condition)
        self._params.extend([start_value, end_value])
        return self
    
    def order_by(self, field: str, direction: str = "ASC") -> 'QueryBuilder':
        """添加ORDER BY
        
        Args:
            field: 排序字段
            direction: 排序方向，ASC或DESC
            
        Returns:
            QueryBuilder实例，支持链式调用
        """
        self._order_by.append(f"{field} {direction}")
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """设置LIMIT
        
        Args:
            count: 限制数量
            
        Returns:
            QueryBuilder实例，支持链式调用
        """
        self._limit = count
        return self
    
    def build(self) -> tuple:
        """构建SQL查询和参数
        
        Returns:
            (query, params) 元组
        """
        # 构建SELECT部分
        select_part = "SELECT " + (", ".join(self._select_fields) if self._select_fields else "*")
        
        # 构建FROM部分
        if not self._from_table:
            raise ValueError("必须指定FROM表名")
        from_part = f"FROM {self._from_table}"
        
        # 构建WHERE部分
        where_part = ""
        if self._where_conditions:
            where_part = "WHERE " + " AND ".join(self._where_conditions)
        
        # 构建ORDER BY部分
        order_part = ""
        if self._order_by:
            order_part = "ORDER BY " + ", ".join(self._order_by)
        
        # 构建LIMIT部分
        limit_part = ""
        if self._limit:
            limit_part = f"LIMIT {self._limit}"
        
        # 组合查询
        query_parts = [select_part, from_part]
        if where_part:
            query_parts.append(where_part)
        if order_part:
            query_parts.append(order_part)
        if limit_part:
            query_parts.append(limit_part)
        
        query = " ".join(query_parts)
        return query, tuple(self._params)
    
def create_db_manager() -> DatabaseManager:
    """创建数据库管理器实例"""
    return DatabaseManager()

def test_database_connection():
    """测试数据库连接"""
    logger.info("开始测试数据库连接")
    
    try:
        with create_db_manager() as db:
            if db.check_connection():
                logger.info("数据库连接测试成功")
                
                # 简单查询测试各个表
                tables = ['audit_results', 'image_audit_results', 'device_map', 
                         'review_tasks', 'review_files', 'review_results']
                
                for table in tables:
                    try:
                        result = db.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch_one=True)
                        count = result[0]['count'] if result else 0
                        logger.info(f"表 {table}: {count} 条记录")
                    except Exception as e:
                        logger.warning(f"无法查询表 {table}: {e}")
                
                return True
            else:
                logger.error("数据库连接测试失败")
                return False
                
    except Exception as e:
        logger.error(f"数据库连接测试异常: {e}")
        return False

if __name__ == "__main__":
    # 运行数据库连接测试
    test_database_connection()