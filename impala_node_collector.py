#!/usr/bin/env python3
"""
Impala Node Metrics Collector
采集单个 Impala 节点的监控指标并导出到 Prometheus
"""

import json
import time
import requests
import logging
import socket
import subprocess
from datetime import datetime
from prometheus_client import start_http_server, Gauge, Counter, Histogram, Info
from typing import Dict, Any, Optional
import argparse
import yaml

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_eth0_ip():
    """获取 eth0 网卡的 IP 地址"""
    try:
        # 方法1: 使用 ip 命令
        result = subprocess.run(['ip', 'addr', 'show', 'eth0'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'inet ' in line and not '127.0.0.1' in line:
                    ip = line.strip().split()[1].split('/')[0]
                    return ip
    except:
        pass
    
    try:
        # 方法2: 使用 socket 连接外部地址获取本地 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        pass
    
    try:
        # 方法3: 使用 hostname -I
        result = subprocess.run(['hostname', '-I'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            ip = result.stdout.strip().split()[0]
            return ip
    except:
        pass
    
    return 'localhost'

class ImpalaNodeCollector:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.impala_host = config.get('impala_host', 'localhost')
        self.impala_port = config.get('impala_port', 25000)
        self.metrics_port = config.get('metrics_port', 9356)
        self.collect_interval = config.get('collect_interval', 30)
        
        # 初始化 Prometheus 指标
        self._init_metrics()
        
    def _init_metrics(self):
        """初始化 Prometheus 指标"""
        # 节点基本信息
        self.node_info = Info('impala_node_info', 'Impala node information')
        
        # 内存指标
        self.memory_rss = Gauge('impala_memory_rss_bytes', 'Resident set size (RSS) memory')
        self.memory_mapped = Gauge('impala_memory_mapped_bytes', 'Total mapped memory')
        self.memory_total_used = Gauge('impala_memory_total_used_bytes', 'Total memory used by TCMalloc and buffer pool')
        
        # TCMalloc 指标
        self.tcmalloc_bytes_in_use = Gauge('impala_tcmalloc_bytes_in_use', 'TCMalloc bytes in use')
        self.tcmalloc_total_reserved = Gauge('impala_tcmalloc_total_reserved_bytes', 'TCMalloc total reserved bytes')
        self.tcmalloc_physical_reserved = Gauge('impala_tcmalloc_physical_reserved_bytes', 'TCMalloc physical reserved bytes')
        
        # JVM 指标
        self.jvm_heap_used = Gauge('impala_jvm_heap_used_bytes', 'JVM heap memory used')
        self.jvm_heap_committed = Gauge('impala_jvm_heap_committed_bytes', 'JVM heap memory committed')
        self.jvm_heap_max = Gauge('impala_jvm_heap_max_bytes', 'JVM heap memory max')
        self.jvm_non_heap_used = Gauge('impala_jvm_non_heap_used_bytes', 'JVM non-heap memory used')
        self.jvm_gc_count = Counter('impala_jvm_gc_count_total', 'JVM garbage collection count')
        self.jvm_gc_time = Counter('impala_jvm_gc_time_seconds_total', 'JVM garbage collection time')
        
        # Buffer Pool 指标
        self.buffer_pool_limit = Gauge('impala_buffer_pool_limit_bytes', 'Buffer pool limit')
        self.buffer_pool_reserved = Gauge('impala_buffer_pool_reserved_bytes', 'Buffer pool reserved')
        self.buffer_pool_system_allocated = Gauge('impala_buffer_pool_system_allocated_bytes', 'Buffer pool system allocated')
        self.buffer_pool_clean_pages_limit = Gauge('impala_buffer_pool_clean_pages_limit_bytes', 'Buffer pool clean pages limit')
        
        # 查询指标
        self.queries_total = Counter('impala_queries_total', 'Total number of queries processed')
        self.queries_registered = Gauge('impala_queries_registered', 'Number of queries currently registered')
        self.queries_executing = Gauge('impala_queries_executing', 'Number of queries currently executing')
        self.queries_waiting = Gauge('impala_queries_waiting', 'Number of queries waiting to close')
        self.queries_spilled = Counter('impala_queries_spilled_total', 'Number of queries that spilled')
        self.queries_expired = Counter('impala_queries_expired_total', 'Number of queries expired')
        
        # 查询执行时间分布
        self.query_duration_histogram = Histogram('impala_query_duration_seconds', 'Query execution duration')
        
        # 查询内存使用
        self.query_memory_usage = Gauge('impala_query_memory_usage_bytes', 'Query memory usage', ['query_id', 'user', 'state'])
        self.query_memory_estimate = Gauge('impala_query_memory_estimate_bytes', 'Query memory estimate', ['query_id', 'user', 'state'])
        
        # 查询详细信息
        self.query_info = Info('impala_query_info', 'Query information', ['query_id'])
        
        # IO 指标
        self.bytes_read_total = Counter('impala_bytes_read_total', 'Total bytes read')
        self.bytes_written_total = Counter('impala_bytes_written_total', 'Total bytes written')
        
        # 线程指标
        self.threads_running = Gauge('impala_threads_running', 'Number of running threads')
        self.threads_created_total = Counter('impala_threads_created_total', 'Total threads created')
        
        # 连接指标
        self.connections_hiveserver2 = Gauge('impala_connections_hiveserver2', 'Active HiveServer2 connections')
        self.connections_beeswax = Gauge('impala_connections_beeswax', 'Active Beeswax connections')
        
        # 准入控制指标
        self.admission_admitted_total = Counter('impala_admission_admitted_total', 'Total admitted queries', ['pool'])
        self.admission_queued = Gauge('impala_admission_queued', 'Currently queued queries', ['pool'])
        self.admission_running = Gauge('impala_admission_running', 'Currently running queries', ['pool'])
        self.admission_rejected_total = Counter('impala_admission_rejected_total', 'Total rejected queries', ['pool'])
        
    def collect_metrics(self):
        """采集指标"""
        try:
            # 获取节点指标
            metrics_data = self._fetch_metrics()
            if metrics_data:
                self._process_metrics(metrics_data)
                
            # 获取查询信息
            queries_data = self._fetch_queries()
            if queries_data:
                self._process_queries(queries_data)
                
            logger.info("Metrics collected successfully")
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            
    def _fetch_metrics(self) -> Optional[Dict]:
        """获取节点指标数据"""
        try:
            url = f"http://{self.impala_host}:{self.impala_port}/metrics?json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            return None
            
    def _fetch_queries(self) -> Optional[Dict]:
        """获取查询信息"""
        try:
            url = f"http://{self.impala_host}:{self.impala_port}/queries?json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch queries: {e}")
            return None
            
    def _process_metrics(self, data: Dict):
        """处理节点指标数据"""
        # 设置节点信息
        process_name = data.get('__common__', {}).get('process-name', 'unknown')
        self.node_info.info({
            'process_name': process_name,
            'host': self.impala_host,
            'port': str(self.impala_port)
        })
        
        # 处理各类指标
        for metric_name, metric_data in data.items():
            if metric_name.startswith('__'):
                continue
                
            try:
                self._process_single_metric(metric_name, metric_data)
            except Exception as e:
                logger.debug(f"Error processing metric {metric_name}: {e}")
                
    def _process_single_metric(self, name: str, data: Any):
        """处理单个指标"""
        if not isinstance(data, dict) or 'value' not in data:
            return
            
        value = self._parse_value(data['value'])
        if value is None:
            return
            
        # 内存指标
        if name == 'memory.rss':
            self.memory_rss.set(value)
        elif name == 'memory.mapped-bytes':
            self.memory_mapped.set(value)
        elif name == 'memory.total-used':
            self.memory_total_used.set(value)
            
        # TCMalloc 指标
        elif name == 'tcmalloc.bytes-in-use':
            self.tcmalloc_bytes_in_use.set(value)
        elif name == 'tcmalloc.total-bytes-reserved':
            self.tcmalloc_total_reserved.set(value)
        elif name == 'tcmalloc.physical-bytes-reserved':
            self.tcmalloc_physical_reserved.set(value)
            
        # JVM 指标
        elif name == 'jvm.heap.current-usage-bytes':
            self.jvm_heap_used.set(value)
        elif name == 'jvm.heap.committed-usage-bytes':
            self.jvm_heap_committed.set(value)
        elif name == 'jvm.heap.max-usage-bytes':
            self.jvm_heap_max.set(value)
        elif name == 'jvm.non-heap.current-usage-bytes':
            self.jvm_non_heap_used.set(value)
        elif name == 'jvm.gc_count':
            self.jvm_gc_count._value._value = value
        elif name == 'jvm.gc_time_millis':
            self.jvm_gc_time._value._value = value / 1000.0  # 转换为秒
            
        # Buffer Pool 指标
        elif name == 'buffer-pool.limit':
            self.buffer_pool_limit.set(value)
        elif name == 'buffer-pool.reserved':
            self.buffer_pool_reserved.set(value)
        elif name == 'buffer-pool.system-allocated':
            self.buffer_pool_system_allocated.set(value)
        elif name == 'buffer-pool.clean-pages-limit':
            self.buffer_pool_clean_pages_limit.set(value)
            
        # 查询指标
        elif name == 'impala-server.num-queries':
            self.queries_total._value._value = value
        elif name == 'impala-server.num-queries-registered':
            self.queries_registered.set(value)
        elif name == 'impala-server.backend-num-queries-executing':
            self.queries_executing.set(value)
        elif name == 'impala-server.num-queries-spilled':
            self.queries_spilled._value._value = value
        elif name == 'impala-server.num-queries-expired':
            self.queries_expired._value._value = value
            
        # IO 指标
        elif name == 'impala-server.io-mgr.bytes-read':
            self.bytes_read_total._value._value = value
        elif name == 'impala-server.io-mgr.bytes-written':
            self.bytes_written_total._value._value = value
            
        # 线程指标
        elif name == 'thread-manager.running-threads':
            self.threads_running.set(value)
        elif name == 'thread-manager.total-threads-created':
            self.threads_created_total._value._value = value
            
        # 连接指标
        elif name == 'impala.thrift-server.hiveserver2-frontend.connections-in-use':
            self.connections_hiveserver2.set(value)
        elif name == 'impala.thrift-server.beeswax-frontend.connections-in-use':
            self.connections_beeswax.set(value)
            
        # 准入控制指标
        elif name.startswith('admission-controller.'):
            self._process_admission_metric(name, value)
            
    def _process_admission_metric(self, name: str, value: float):
        """处理准入控制指标"""
        parts = name.split('.')
        if len(parts) < 3:
            return
            
        pool_name = parts[-1] if parts[-1] != 'default-pool' else 'default'
        metric_type = '.'.join(parts[1:-1])
        
        if metric_type == 'total-admitted':
            self.admission_admitted_total.labels(pool=pool_name)._value._value = value
        elif metric_type == 'local-num-queued':
            self.admission_queued.labels(pool=pool_name).set(value)
        elif metric_type == 'agg-num-running':
            self.admission_running.labels(pool=pool_name).set(value)
        elif metric_type == 'total-rejected':
            self.admission_rejected_total.labels(pool=pool_name)._value._value = value
            
    def _process_queries(self, data: Dict):
        """处理查询信息"""
        # 处理正在执行的查询
        in_flight_queries = data.get('in_flight_queries', [])
        waiting_count = 0
        executing_count = 0
        
        # 清除旧的查询指标
        self.query_memory_usage.clear()
        self.query_memory_estimate.clear()
        
        for query in in_flight_queries:
            query_id = query.get('query_id', '')
            user = query.get('effective_user', '')
            state = query.get('state', '')
            
            # 统计等待和执行中的查询
            if query.get('waiting', False):
                waiting_count += 1
            if query.get('executing', False):
                executing_count += 1
                
            # 内存使用指标
            mem_usage = self._parse_value(query.get('mem_usage', '0'))
            mem_estimate = self._parse_value(query.get('mem_est', '0'))
            
            if mem_usage is not None:
                self.query_memory_usage.labels(query_id=query_id, user=user, state=state).set(mem_usage)
            if mem_estimate is not None:
                self.query_memory_estimate.labels(query_id=query_id, user=user, state=state).set(mem_estimate)
                
            # 查询执行时间
            duration_str = query.get('duration', '0')
            duration_seconds = self._parse_duration(duration_str)
            if duration_seconds is not None:
                self.query_duration_histogram.observe(duration_seconds)
                
            # 查询详细信息
            self.query_info.labels(query_id=query_id).info({
                'user': user,
                'state': state,
                'default_db': query.get('default_db', ''),
                'stmt_type': query.get('stmt_type', ''),
                'resource_pool': query.get('resource_pool', ''),
                'start_time': query.get('start_time', ''),
                'duration': duration_str,
                'bytes_read': query.get('bytes_read', '0'),
                'bytes_sent': query.get('bytes_sent', '0'),
                'rows_fetched': str(query.get('rows_fetched', 0))
            })
            
        # 更新等待和执行中的查询数量
        self.queries_waiting.set(waiting_count)
        # executing count 从 metrics 中获取更准确
        
    def _parse_value(self, value_str: str) -> Optional[float]:
        """解析数值字符串"""
        if not isinstance(value_str, str):
            if isinstance(value_str, (int, float)):
                return float(value_str)
            return None
            
        value_str = value_str.strip()
        if not value_str or value_str == 'N/A':
            return None
            
        # 处理带单位的数值
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4,
            'K': 1000,
            'M': 1000**2,
            'G': 1000**3,
            'T': 1000**4
        }
        
        # 移除逗号
        value_str = value_str.replace(',', '')
        
        # 查找单位
        for unit, multiplier in multipliers.items():
            if value_str.endswith(unit):
                try:
                    number = float(value_str[:-len(unit)].strip())
                    return number * multiplier
                except ValueError:
                    continue
                    
        # 尝试直接解析数字
        try:
            return float(value_str)
        except ValueError:
            return None
            
    def _parse_duration(self, duration_str: str) -> Optional[float]:
        """解析时间长度字符串，返回秒数"""
        if not duration_str:
            return None
            
        duration_str = duration_str.strip()
        if not duration_str or duration_str == 'N/A':
            return None
            
        # 处理各种时间格式
        total_seconds = 0.0
        
        # 处理 "1h2m3s" 格式
        import re
        time_pattern = r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?(?:(\d+(?:\.\d+)?)ms)?(?:(\d+(?:\.\d+)?)us)?'
        match = re.match(time_pattern, duration_str)
        
        if match:
            hours, minutes, seconds, milliseconds, microseconds = match.groups()
            
            if hours:
                total_seconds += int(hours) * 3600
            if minutes:
                total_seconds += int(minutes) * 60
            if seconds:
                total_seconds += float(seconds)
            if milliseconds:
                total_seconds += float(milliseconds) / 1000
            if microseconds:
                total_seconds += float(microseconds) / 1000000
                
            return total_seconds
            
        # 尝试直接解析毫秒
        if duration_str.endswith('ms'):
            try:
                return float(duration_str[:-2]) / 1000
            except ValueError:
                pass
                
        return None
        
    def start_server(self):
        """启动 Prometheus 指标服务器"""
        start_http_server(self.metrics_port)
        logger.info(f"Prometheus metrics server started on port {self.metrics_port}")
        
    def run(self):
        """运行采集器"""
        self.start_server()
        
        logger.info(f"Starting Impala node collector for {self.impala_host}:{self.impala_port}")
        logger.info(f"Metrics will be available at http://localhost:{self.metrics_port}/metrics")
        
        while True:
            try:
                self.collect_metrics()
                time.sleep(self.collect_interval)
            except KeyboardInterrupt:
                logger.info("Shutting down collector...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(self.collect_interval)

def load_config(config_file: str) -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config file {config_file}: {e}")
        return {}

def main():
    parser = argparse.ArgumentParser(description='Impala Node Metrics Collector')
    parser.add_argument('--config', '-c', default='node_config.yaml', help='Configuration file path')
    parser.add_argument('--host', help='Impala host (overrides config)')
    parser.add_argument('--port', type=int, help='Impala port (overrides config)')
    parser.add_argument('--metrics-port', type=int, help='Prometheus metrics port (overrides config)')
    
    args = parser.parse_args()
    
    # 获取本机 IP 地址
    local_ip = get_eth0_ip()
    logger.info(f"Detected local IP: {local_ip}")
    
    # 加载配置
    config = load_config(args.config)
    
    # 命令行参数覆盖配置文件
    if args.host:
        config['impala_host'] = args.host
    if args.port:
        config['impala_port'] = args.port
    if args.metrics_port:
        config['metrics_port'] = args.metrics_port
        
    # 设置默认值，使用自动获取的 IP
    config.setdefault('impala_host', local_ip)
    config.setdefault('impala_port', 25000)
    config.setdefault('metrics_port', 9356)
    config.setdefault('collect_interval', 30)
    
    # 启动采集器
    collector = ImpalaNodeCollector(config)
    collector.run()

if __name__ == '__main__':
    main()
