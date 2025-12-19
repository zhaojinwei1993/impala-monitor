#!/usr/bin/env python3
"""
Impala Metrics Exporter
直接获取指标的 value 值
"""

import json
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ImpalaExporter:
    """Impala 指标导出器"""
    
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
    
    def get_metric_value(self, metrics, metric_name):
        """从metrics列表中获取指定指标的value值"""
        for metric in metrics:
            if metric.get("name") == metric_name:
                return metric.get("value", 0)
        return 0
    
    def get_limitmemory_metrics(self, metrics):
        """获取内存限制相关指标"""
        return {
            "mem_tracker_process_limit": self.get_metric_value(metrics, "mem-tracker.process.limit")
        }

    def get_memory_metrics(self, metrics):
        """获取内存相关指标"""
        return {
            "memory_rss": self.get_metric_value(metrics, "memory.rss"),
            "memory_total_used": self.get_metric_value(metrics, "memory.total-used")
        }

    def get_jvm_metrics(self, metrics):
        """获取JVM相关指标"""
        return {
            "jvm_total_committed_usage_bytes": self.get_metric_value(metrics, "jvm.total.committed-usage-bytes"),
            "jvm_total_current_usage_bytes": self.get_metric_value(metrics, "jvm.total.current-usage-bytes"),
            "jvm_heap_committed_usage_bytes": self.get_metric_value(metrics, "jvm.heap.committed-usage-bytes"),
            "jvm_heap_current_usage_bytes": self.get_metric_value(metrics, "jvm.heap.current-usage-bytes"),
            "jvm_non_heap_committed_usage_bytes": self.get_metric_value(metrics, "jvm.non-heap.committed-usage-bytes"),
            "jvm_non_heap_current_usage_bytes": self.get_metric_value(metrics, "jvm.non-heap.current-usage-bytes"),
            "jvm_gc_time_millis": self.get_metric_value(metrics, "jvm.gc_time_millis"),
            "jvm_gc_num_warn_threshold_exceeded": self.get_metric_value(metrics, "jvm.gc_num_warn_threshold_exceeded")
        }

    def get_impala_server_metrics(self, metrics):
        """获取Impala Server相关指标"""
        return {
            "impala_server_num_open_beeswax_sessions": self.get_metric_value(metrics, "impala-server.num-open-beeswax-sessions"),
            "impala_server_num_open_hiveserver2_sessions": self.get_metric_value(metrics, "impala-server.num-open-hiveserver2-sessions")
        }
    
    def get_query_details(self, queries_data):
        """获取查询详细信息"""
        query_details = []
        in_flight_queries = queries_data.get("in_flight_queries", [])
        
        for query in in_flight_queries:
            detail = {
                "effective_user": query.get("effective_user", ""),
                "stmt": query.get("stmt", ""),
                "start_time": query.get("start_time", ""),
                "duration": query.get("duration", ""),
                "state": query.get("state", ""),
                "mem_usage": query.get("mem_usage", 0),
                "query_id": query.get("query_id", "")
            }
            
            # 如果是已完成的查询，添加结束时间
            if "end_time" in query:
                detail["end_time"] = query.get("end_time", "")
            
            query_details.append(detail)
        
        return query_details
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        metrics_data = self._get_metrics_data()
        queries_data = self._get_queries_data()
        
        result = {}
        
        if metrics_data:
            # 获取根级别的metrics
            root_metrics = metrics_data.get("metric_group", {}).get("metrics", [])
            result.update(self.get_limitmemory_metrics(root_metrics))
            
            # 获取子组的metrics
            child_groups = metrics_data.get("metric_group", {}).get("child_groups", [])
            for child_group in child_groups:
                group_name = child_group.get("name")
                group_metrics = child_group.get("metrics", [])
                
                if group_name == "memory":
                    result.update(self.get_memory_metrics(group_metrics))
                elif group_name == "jvm":
                    result.update(self.get_jvm_metrics(group_metrics))
                elif group_name == "impala-server":
                    result.update(self.get_impala_server_metrics(group_metrics))
        
        if queries_data:
            result.update({
                "num_in_flight_queries": queries_data.get("num_in_flight_queries", 0),
                "num_executing_queries": queries_data.get("num_executing_queries", 0),
                "num_waiting_queries": queries_data.get("num_waiting_queries", 0)
            })
            result["query_details"] = self.get_query_details(queries_data)
        
        return result
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            response = self.session.get(self.metrics_url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Successfully connected to Impala metrics endpoint")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to metrics endpoint: {e}")
        
        try:
            response = self.session.get(self.queries_url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Successfully connected to Impala queries endpoint")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to queries endpoint: {e}")
        
        return False
