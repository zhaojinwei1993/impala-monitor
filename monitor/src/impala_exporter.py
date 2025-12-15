#!/usr/bin/env python3
"""
Impala Metrics Exporter
基于 metrics 和 queries 接口采集 Impala 指标
"""

import json
import requests
import logging
import socket
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ImpalaExporter:
    """Impala 指标导出器，通过 metrics 和 queries 接口获取指标"""
    
    def __init__(self, host: str, port: int = 25000):
        self.host = host
        self.port = port
        self.metrics_url = f"http://{host}:{port}/metrics?json"
        self.queries_url = f"http://{host}:{port}/queries?json"
        self.session = requests.Session()
        self.session.timeout = 10
    
    def _get_metrics_data(self) -> Optional[Dict]:
        """获取 metrics 接口数据"""
        try:
            response = self.session.get(self.metrics_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get metrics data: {e}")
            return None
    
    def _get_queries_data(self) -> Optional[Dict]:
        """获取查询数据"""
        try:
            response = self.session.get(self.queries_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get queries data: {e}")
            return None
    
    def get_jvm_metrics(self) -> Optional[Dict]:
        """获取 JVM 指标 - 从 metrics 接口获取"""
        metrics_data = self._get_metrics_data()
        if metrics_data:
            return self.parse_memory_metrics(metrics_data)
        return None
    
    def parse_memory_metrics(self, data):
        """解析内存指标"""
        metrics = {}
        
        def find_metric_group(obj, group_name):
            """递归查找指定名称的metric group"""
            if isinstance(obj, dict):
                if obj.get('name') == group_name and 'metrics' in obj:
                    return obj['metrics']
                if 'child_groups' in obj:
                    for child in obj['child_groups']:
                        result = find_metric_group(child, group_name)
                        if result:
                            return result
                # 递归搜索所有值
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        result = find_metric_group(value, group_name)
                        if result:
                            return result
            elif isinstance(obj, list):
                for item in obj:
                    result = find_metric_group(item, group_name)
                    if result:
                        return result
            return None
        
        # TCMalloc指标
        tcmalloc_metrics = find_metric_group(data, 'tcmalloc')
        if tcmalloc_metrics:
            for metric in tcmalloc_metrics:
                name = metric.get('name', '')
                value = metric.get('value', 0)
                if name == 'tcmalloc.bytes-in-use':
                    metrics['tcmalloc_bytes_in_use'] = value
                elif name == 'tcmalloc.physical-bytes-reserved':
                    metrics['tcmalloc_physical_bytes'] = value
        
        # Memory指标
        memory_metrics = find_metric_group(data, 'memory')
        if memory_metrics:
            for metric in memory_metrics:
                name = metric.get('name', '')
                value = metric.get('value', 0)
                if name == 'memory.rss':
                    metrics['memory_rss'] = value
                elif name == 'memory.total-used':
                    metrics['memory_total_used'] = value
        
        # JVM指标
        jvm_metrics = find_metric_group(data, 'jvm')
        if jvm_metrics:
            for metric in jvm_metrics:
                name = metric.get('name', '')
                value = metric.get('value', 0)
                if name == 'jvm.heap.current-usage-bytes':
                    metrics['jvm_heap_used'] = value
                elif name == 'jvm.heap.max-usage-bytes':
                    metrics['jvm_heap_max'] = value
        
        return metrics
    
    def get_memory_metrics(self) -> Optional[Dict]:
        """获取内存指标"""
        metrics_data = self._get_metrics_data()
        if metrics_data:
            return self.parse_memory_metrics(metrics_data)
        return None
    
    def get_system_metrics(self) -> Optional[Dict]:
        """获取系统资源指标"""
        metrics_data = self._get_metrics_data()
        if metrics_data:
            system_data = {}
            
            # 提取系统相关指标
            system_keys = ['thread', 'connection', 'io-mgr', 'rpc', 'disk']
            for key, value in metrics_data.items():
                if any(sys_key in key.lower() for sys_key in system_keys):
                    if isinstance(value, dict) and 'value' in value:
                        system_data[key] = value['value']
                    else:
                        system_data[key] = value
            
            return system_data if system_data else None
        
        return None
    
    def get_query_metrics(self) -> Optional[Dict]:
        """获取查询指标 - 返回当前瞬时值而非累计值"""
        queries_data = self._get_queries_data()
        if not queries_data:
            return None
        
        # 统计当前查询状态
        query_states = {
            'running': 0,
            'finished': 0,
            'exception': 0,
            'cancelled': 0,
            'waiting': 0,
            'executing': 0
        }
        
        # 处理正在执行的查询
        in_flight_queries = queries_data.get('in_flight_queries', [])
        for query in in_flight_queries:
            state = query.get('state', '').lower()
            if state in query_states:
                query_states[state] += 1
            
            # 检查查询是否在等待或执行中
            if query.get('waiting', False):
                query_states['waiting'] += 1
            if query.get('executing', False):
                query_states['executing'] += 1
        
        # 处理已完成的查询（只统计最近的）
        completed_queries = queries_data.get('completed_queries', [])
        # 只统计最近完成的查询，避免累计值
        recent_completed = completed_queries[-100:] if len(completed_queries) > 100 else completed_queries
        
        for query in recent_completed:
            state = query.get('state', '').lower()
            if state in ['finished', 'exception', 'cancelled']:
                # 这里不累加，因为我们要的是瞬时值
                pass
        
        return {
            'current_states': query_states,
            'in_flight_count': len(in_flight_queries),
            'total_queries': len(in_flight_queries) + len(completed_queries)
        }
    
    def get_admission_control_metrics(self) -> Optional[Dict]:
        """获取准入控制指标"""
        metrics_data = self._get_metrics_data()
        if metrics_data:
            admission_data = {}
            
            for key, value in metrics_data.items():
                if 'admission-controller' in key:
                    if isinstance(value, dict) and 'value' in value:
                        admission_data[key] = value['value']
                    else:
                        admission_data[key] = value
            
            return admission_data if admission_data else None
        
        return None
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            'jvm': self.get_jvm_metrics(),
            'memory': self.get_memory_metrics(),
            'system': self.get_system_metrics(),
            'queries': self.get_query_metrics(),
            'admission': self.get_admission_control_metrics()
        }
    
    def test_connection(self) -> bool:
        """测试连接"""
        # 直接测试metrics端点，这是我们实际需要的
        try:
            response = self.session.get(self.metrics_url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Successfully connected to Impala metrics endpoint")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to metrics endpoint: {e}")
        
        # 如果metrics失败，测试queries端点
        try:
            response = self.session.get(self.queries_url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Successfully connected to Impala queries endpoint")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to queries endpoint: {e}")
        
        return False
