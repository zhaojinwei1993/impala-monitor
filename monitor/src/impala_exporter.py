#!/usr/bin/env python3
"""
Impala Metrics Exporter
基于 JMX 接口采集 Impala 指标，参考 Hadoop 监控项目结构
"""

import json
import requests
import logging
import socket
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ImpalaExporter:
    """Impala 指标导出器，通过 JMX 接口获取指标"""
    
    def __init__(self, host: str, port: int = 25000):
        self.host = host
        self.port = port
        self.jmx_url = f"http://{host}:{port}/jmx"
        self.metrics_url = f"http://{host}:{port}/metrics?json"
        self.queries_url = f"http://{host}:{port}/queries?json"
        self.session = requests.Session()
        self.session.timeout = 10
        
    def _get_jmx_data(self, query: str = None) -> Optional[Dict]:
        """获取 JMX 数据"""
        try:
            url = self.jmx_url
            if query:
                url = f"{self.jmx_url}?qry={query}"
            
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            if 'beans' in data and data['beans']:
                return data['beans']
            return data
            
        except Exception as e:
            logger.error(f"Failed to get JMX data from {url}: {e}")
            return None
    
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
        """获取 JVM 指标"""
        # 尝试多种可能的 JVM 指标查询
        jvm_queries = [
            "java.lang:type=Memory",
            "java.lang:type=MemoryPool,name=*",
            "java.lang:type=GarbageCollector,name=*",
            "java.lang:type=Runtime"
        ]
        
        jvm_data = {}
        for query in jvm_queries:
            data = self._get_jmx_data(query)
            if data:
                if isinstance(data, list):
                    for bean in data:
                        jvm_data.update(bean)
                else:
                    jvm_data.update(data)
        
        # 如果 JMX 没有数据，尝试从 metrics 接口获取
        if not jvm_data:
            metrics_data = self._get_metrics_data()
            if metrics_data:
                jvm_data = self._extract_jvm_from_metrics(metrics_data)
        
        return jvm_data if jvm_data else None
    
    def get_memory_metrics(self) -> Optional[Dict]:
        """获取内存指标"""
        # 首先尝试从 metrics 接口获取
        metrics_data = self._get_metrics_data()
        if metrics_data:
            memory_data = {}
            
            # 提取内存相关指标
            for key, value in metrics_data.items():
                if any(mem_key in key.lower() for mem_key in ['memory', 'mem-', 'tcmalloc', 'buffer-pool']):
                    if isinstance(value, dict) and 'value' in value:
                        memory_data[key] = value['value']
                    else:
                        memory_data[key] = value
            
            return memory_data if memory_data else None
        
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
    
    def _extract_jvm_from_metrics(self, metrics_data: Dict) -> Dict:
        """从 metrics 数据中提取 JVM 指标"""
        jvm_data = {}
        
        for key, value in metrics_data.items():
            if key.startswith('jvm.'):
                if isinstance(value, dict) and 'value' in value:
                    jvm_data[key] = value['value']
                else:
                    jvm_data[key] = value
        
        return jvm_data
    
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
