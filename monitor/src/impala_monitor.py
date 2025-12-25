#!/usr/bin/env python3
"""
Impala Monitor
Impala 监控收集器，基于 metrics 和 queries 接口
支持主机IP和主机名标签
"""

import time
import logging
import argparse
import yaml
import socket
import subprocess
from typing import Dict, Any, Optional
from prometheus_client import start_http_server, Gauge, Counter, Info
from impala_exporter import ImpalaExporter

# 配置日志
import os
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'impala_monitor.log')

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)
logger = logging.getLogger(__name__)


def get_local_ip():
    """获取本地 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            result = subprocess.run(['hostname', '-I'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().split()[0]
        except:
            pass
    return 'localhost'


def get_hostname():
    """获取主机名"""
    try:
        return socket.gethostname()
    except:
        return 'unknown'


class ImpalaMonitor:
    """Impala 监控收集器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.impala_host = config.get('impala_host', get_local_ip())
        self.impala_port = config.get('impala_port', 25000)
        self.metrics_port = config.get('metrics_port', 9356)
        self.collect_interval = config.get('collect_interval', 30)
        
        # 获取主机信息
        self.host_ip = get_local_ip()
        self.hostname = get_hostname()
        
        # 初始化导出器
        self.exporter = ImpalaExporter(self.impala_host, self.impala_port)
        
        # 初始化 Prometheus 指标
        self._init_prometheus_metrics()
        
    def _init_prometheus_metrics(self):
        """初始化 Prometheus 指标，添加主机标签"""
        # 通用标签
        common_labels = ['host_ip', 'hostname']
        
        # 节点信息
        self.node_info = Info('impala_node_info', 'Impala node information', common_labels)
        
        # 内存限制指标
        self.mem_tracker_limit = Gauge('impala_mem_tracker_process_limit', 'Process memory limit', common_labels)
        
        # 内存使用指标
        self.memory_rss = Gauge('impala_memory_rss', 'RSS memory usage', common_labels)
        self.memory_total_used = Gauge('impala_memory_total_used', 'Total memory used', common_labels)
        
        # JVM 指标
        self.jvm_total_committed = Gauge('impala_jvm_total_committed_bytes', 'JVM total committed bytes', common_labels)
        self.jvm_total_current = Gauge('impala_jvm_total_current_bytes', 'JVM total current bytes', common_labels)
        self.jvm_heap_committed = Gauge('impala_jvm_heap_committed_bytes', 'JVM heap committed bytes', common_labels)
        self.jvm_heap_current = Gauge('impala_jvm_heap_current_bytes', 'JVM heap current bytes', common_labels)
        self.jvm_non_heap_committed = Gauge('impala_jvm_non_heap_committed_bytes', 'JVM non-heap committed bytes', common_labels)
        self.jvm_non_heap_current = Gauge('impala_jvm_non_heap_current_bytes', 'JVM non-heap current bytes', common_labels)
        self.jvm_gc_time = Gauge('impala_jvm_gc_time_millis', 'JVM GC time in milliseconds', common_labels)
        self.jvm_gc_warn_threshold = Gauge('impala_jvm_gc_warn_threshold_exceeded', 'JVM GC warn threshold exceeded', common_labels)
        
        # Impala Server 指标
        self.beeswax_sessions = Gauge('impala_server_beeswax_sessions', 'Number of open Beeswax sessions', common_labels)
        self.hiveserver2_sessions = Gauge('impala_server_hiveserver2_sessions', 'Number of open HiveServer2 sessions', common_labels)
        
        # 查询指标
        self.queries_in_flight = Gauge('impala_queries_in_flight', 'Number of in-flight queries', common_labels)
        self.queries_executing = Gauge('impala_queries_executing', 'Number of executing queries', common_labels)
        self.queries_waiting = Gauge('impala_queries_waiting', 'Number of waiting queries', common_labels)
        
        # 具体查询指标 - 带 query_id 标签
        query_labels = common_labels + ['query_id', 'effective_user', 'state']
        self.query_memory_usage = Gauge('impala_query_memory_usage_bytes', 'Query memory usage', query_labels)
        self.query_duration = Gauge('impala_query_duration_seconds', 'Query duration', query_labels)
        self.query_start_time = Gauge('impala_query_start_time', 'Query start timestamp', query_labels)
        self.query_end_time = Gauge('impala_query_end_time', 'Query end timestamp', query_labels)
        self.query_info = Info('impala_query_info', 'Query statement information', query_labels)
        #
    def _get_host_labels(self) -> Dict[str, str]:
        """获取主机标签"""
        return {
            'host_ip': self.host_ip,
            'hostname': self.hostname
        }
        
    def collect_metrics(self):
        """采集所有指标"""
        try:
            logger.info(f"Collecting metrics from {self.impala_host}:{self.impala_port} (Host: {self.hostname}/{self.host_ip})")
            
            # 测试连接
            if not self.exporter.test_connection():
                logger.error(f"Cannot connect to Impala at {self.impala_host}:{self.impala_port}")
                return
            
            # 获取所有指标
            all_metrics = self.exporter.get_all_metrics()
            
            # 获取主机标签
            host_labels = self._get_host_labels()
            
            # 设置节点信息
            self.node_info.labels(**host_labels).info({
                'impala_host': self.impala_host,
                'impala_port': str(self.impala_port),
                'version': 'unknown'
            })
            
            # 处理各类指标
            self._process_metrics(all_metrics, host_labels)
            
            logger.info("Metrics collected successfully")
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    def _process_metrics(self, all_metrics: Dict[str, Any], host_labels: Dict[str, str]):
        """处理所有指标"""
        # 内存限制指标
        mem_limit = all_metrics.get('mem_tracker_process_limit', 0)
        if mem_limit:
            self.mem_tracker_limit.labels(**host_labels).set(mem_limit)
        
        # 内存使用指标
        memory_rss = all_metrics.get('memory_rss', 0)
        memory_total = all_metrics.get('memory_total_used', 0)
        if memory_rss:
            self.memory_rss.labels(**host_labels).set(memory_rss)
        if memory_total:
            self.memory_total_used.labels(**host_labels).set(memory_total)
        
        # JVM 指标
        jvm_metrics = {
            'jvm_total_committed_usage_bytes': self.jvm_total_committed,
            'jvm_total_current_usage_bytes': self.jvm_total_current,
            'jvm_heap_committed_usage_bytes': self.jvm_heap_committed,
            'jvm_heap_current_usage_bytes': self.jvm_heap_current,
            'jvm_non_heap_committed_usage_bytes': self.jvm_non_heap_committed,
            'jvm_non_heap_current_usage_bytes': self.jvm_non_heap_current,
            'jvm_gc_time_millis': self.jvm_gc_time,
            'jvm_gc_num_warn_threshold_exceeded': self.jvm_gc_warn_threshold
        }
        
        for metric_name, prometheus_gauge in jvm_metrics.items():
            value = all_metrics.get(metric_name, 0)
            if value:
                prometheus_gauge.labels(**host_labels).set(value)
        
        # Impala Server 指标
        beeswax = all_metrics.get('impala_server_num_open_beeswax_sessions', 0)
        hiveserver2 = all_metrics.get('impala_server_num_open_hiveserver2_sessions', 0)
        if beeswax:
            self.beeswax_sessions.labels(**host_labels).set(beeswax)
        if hiveserver2:
            self.hiveserver2_sessions.labels(**host_labels).set(hiveserver2)
        
        # 查询指标
        in_flight = all_metrics.get('num_in_flight_queries', 0)
        executing = all_metrics.get('num_executing_queries', 0)
        waiting = all_metrics.get('num_waiting_queries', 0)
        
        self.queries_in_flight.labels(**host_labels).set(in_flight)
        self.queries_executing.labels(**host_labels).set(executing)
        self.queries_waiting.labels(**host_labels).set(waiting)
        
        # 处理运行中查询
        query_details = all_metrics.get('query_details', [])
        self._process_query_list(query_details, host_labels, "in_flight")
        
        # 处理已完成查询
        completed_queries = all_metrics.get('completed_queries', [])
        self._process_query_list(completed_queries, host_labels, "completed")
    
    def _process_query_list(self, queries: list, host_labels: Dict[str, str], query_type: str):
        """处理查询列表"""
        logger.info(f"Processing {len(queries)} {query_type} queries")
        
        processed_count = 0
        skipped_count = 0
        
        for query in queries:
            # 过滤掉 GET_SCHEMAS 查询
            stmt = query.get('stmt', '')
            if stmt == 'GET_SCHEMAS':
                skipped_count += 1
                logger.debug(f"Skipped GET_SCHEMAS query: {query.get('query_id', 'unknown')}")
                continue
            
            query_id = query.get('query_id', '')
            effective_user = query.get('effective_user', '')
            state = query.get('state', '')
            
            query_labels = {
                **host_labels,
                'query_id': query_id,
                'effective_user': effective_user,
                'state': state
            }
            
            logger.debug(f"Processing {query_type} query {query_id} for user {effective_user}")
            
            # 内存使用 (转换为字节)
            mem_usage = query.get('mem_usage', 0)
            if isinstance(mem_usage, str) and mem_usage != '0':
                mem_bytes = self._parse_memory_string(mem_usage)
                if mem_bytes:
                    self.query_memory_usage.labels(**query_labels).set(mem_bytes)
                    logger.debug(f"Set memory usage for {query_id}: {mem_bytes} bytes")
                else:
                    logger.warning(f"Failed to parse memory usage '{mem_usage}' for query {query_id}")
            else:
                logger.debug(f"No memory usage data for query {query_id}: {mem_usage}")
            
            # 执行时间 (转换为秒)
            duration = query.get('duration', '')
            if duration:
                duration_seconds = self._parse_duration_string(duration)
                if duration_seconds:
                    self.query_duration.labels(**query_labels).set(duration_seconds)
                    logger.debug(f"Set duration for {query_id}: {duration_seconds} seconds")
                else:
                    logger.warning(f"Failed to parse duration '{duration}' for query {query_id}")
            else:
                logger.debug(f"No duration data for query {query_id}")
            
            # 开始时间 (转换为时间戳)
            start_time = query.get('start_time', '')
            if start_time:
                start_timestamp = self._parse_time_string(start_time)
                if start_timestamp:
                    self.query_start_time.labels(**query_labels).set(start_timestamp)
                    logger.debug(f"Set start time for {query_id}: {start_timestamp}")
                else:
                    logger.warning(f"Failed to parse start time '{start_time}' for query {query_id}")
            else:
                logger.debug(f"No start time data for query {query_id}")
            
            # 结束时间 (如果存在)
            end_time = query.get('end_time', '')
            if end_time:
                end_timestamp = self._parse_time_string(end_time)
                if end_timestamp:
                    self.query_end_time.labels(**query_labels).set(end_timestamp)
                    logger.debug(f"Set end time for {query_id}: {end_timestamp}")
                else:
                    logger.warning(f"Failed to parse end time '{end_time}' for query {query_id}")
            else:
                logger.debug(f"No end time data for query {query_id} (query may be running)")
            
            # 查询语句
            if stmt:
                self.query_info.labels(**query_labels).info({'statement': stmt[:1000]})  # 限制长度
                logger.debug(f"Set query statement for {query_id}: {stmt[:100]}...")
            else:
                logger.debug(f"No statement data for query {query_id}")
            
            processed_count += 1
        
        logger.info(f"Processed {processed_count} {query_type} queries, skipped {skipped_count} GET_SCHEMAS queries")
    
    def _parse_memory_string(self, mem_str: str) -> Optional[float]:
        """解析内存字符串为字节数"""
        if not mem_str or mem_str == '0':
            return None
        
        mem_str = mem_str.strip().upper()
        multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        
        for unit, multiplier in multipliers.items():
            if mem_str.endswith(unit):
                try:
                    number = float(mem_str[:-len(unit)].strip())
                    return number * multiplier
                except ValueError:
                    continue
        
        try:
            return float(mem_str)
        except ValueError:
            return None
    
    def _parse_duration_string(self, duration_str: str) -> Optional[float]:
        """解析时间字符串为秒数"""
        if not duration_str:
            return None
        
        # 格式如: "1h2m3s" 或 "2m30s" 或 "45s"
        import re
        pattern = r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?'
        match = re.match(pattern, duration_str.strip())
        
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = float(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        
        return None
    
    def _parse_time_string(self, time_str: str) -> Optional[float]:
        """解析时间字符串为时间戳"""
        if not time_str:
            return None
        
        try:
            from datetime import datetime
            # 假设格式为 "2023-12-19 15:30:45"
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return dt.timestamp()
        except ValueError:
            try:
                # 尝试其他格式
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return dt.timestamp()
            except ValueError:
                return None
    
    def start_server(self):
        """启动 Prometheus 指标服务器"""
        start_http_server(self.metrics_port)
        logger.info(f"Prometheus metrics server started on port {self.metrics_port}")
    
    def run(self):
        """运行监控收集器"""
        self.start_server()
        
        logger.info(f"Starting Impala Monitor for {self.impala_host}:{self.impala_port}")
        logger.info(f"Host Info: {self.hostname} ({self.host_ip})")
        logger.info(f"Metrics available at http://localhost:{self.metrics_port}/metrics")
        
        while True:
            try:
                self.collect_metrics()
                time.sleep(self.collect_interval)
            except KeyboardInterrupt:
                logger.info("Shutting down monitor...")
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
    parser = argparse.ArgumentParser(description='Impala Monitor')
    parser.add_argument('--config', '-c', default='../config/node_config.yaml', help='Configuration file path')
    parser.add_argument('--host', help='Impala host (overrides config)')
    parser.add_argument('--port', type=int, help='Impala port (overrides config)')
    parser.add_argument('--metrics-port', type=int, help='Prometheus metrics port (overrides config)')
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    if args.host:
        config['impala_host'] = args.host
    if args.port:
        config['impala_port'] = args.port
    if args.metrics_port:
        config['metrics_port'] = args.metrics_port
    
    config.setdefault('impala_host', get_local_ip())
    config.setdefault('impala_port', 25000)
    config.setdefault('metrics_port', 9356)
    config.setdefault('collect_interval', 30)
    
    monitor = ImpalaMonitor(config)
    monitor.run()


if __name__ == '__main__':
    main()
