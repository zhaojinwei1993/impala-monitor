#!/usr/bin/env python3
"""
Impala Monitor
Impala 监控收集器，基于 JMX 和 metrics 接口
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        
        # JVM 指标
        self.jvm_heap_used = Gauge('impala_jvm_heap_used_bytes', 'JVM heap memory used', common_labels)
        self.jvm_heap_max = Gauge('impala_jvm_heap_max_bytes', 'JVM heap memory max', common_labels)
        self.jvm_heap_committed = Gauge('impala_jvm_heap_committed_bytes', 'JVM heap memory committed', common_labels)
        self.jvm_non_heap_used = Gauge('impala_jvm_non_heap_used_bytes', 'JVM non-heap memory used', common_labels)
        self.jvm_gc_count = Gauge('impala_jvm_gc_count_total', 'JVM garbage collection count', common_labels)
        self.jvm_gc_time = Gauge('impala_jvm_gc_time_seconds_total', 'JVM garbage collection time', common_labels)
        
        # 内存指标
        self.memory_rss = Gauge('impala_memory_rss_bytes', 'Resident set size memory', common_labels)
        self.memory_mapped = Gauge('impala_memory_mapped_bytes', 'Mapped memory', common_labels)
        self.memory_total_used = Gauge('impala_memory_total_used_bytes', 'Total memory used', common_labels)
        self.tcmalloc_in_use = Gauge('impala_tcmalloc_in_use_bytes', 'TCMalloc memory in use', common_labels)
        self.tcmalloc_reserved = Gauge('impala_tcmalloc_reserved_bytes', 'TCMalloc reserved memory', common_labels)
        
        # Buffer Pool 指标
        self.buffer_pool_limit = Gauge('impala_buffer_pool_limit_bytes', 'Buffer pool limit', common_labels)
        self.buffer_pool_reserved = Gauge('impala_buffer_pool_reserved_bytes', 'Buffer pool reserved', common_labels)
        self.buffer_pool_allocated = Gauge('impala_buffer_pool_allocated_bytes', 'Buffer pool allocated', common_labels)
        
        # 查询状态指标 - 瞬时值
        self.queries_running = Gauge('impala_queries_running_current', 'Currently running queries', common_labels)
        self.queries_waiting = Gauge('impala_queries_waiting_current', 'Currently waiting queries', common_labels)
        self.queries_executing = Gauge('impala_queries_executing_current', 'Currently executing queries', common_labels)
        self.queries_finished = Gauge('impala_queries_finished_current', 'Recently finished queries', common_labels)
        self.queries_exception = Gauge('impala_queries_exception_current', 'Queries with exceptions', common_labels)
        self.queries_cancelled = Gauge('impala_queries_cancelled_current', 'Cancelled queries', common_labels)
        
        # 查询总数
        self.queries_in_flight = Gauge('impala_queries_in_flight_total', 'Total in-flight queries', common_labels)
        
        # 系统资源指标
        self.threads_running = Gauge('impala_threads_running', 'Running threads', common_labels)
        self.threads_created = Gauge('impala_threads_created_total', 'Total threads created', common_labels)
        self.connections_hiveserver2 = Gauge('impala_connections_hiveserver2', 'HiveServer2 connections', common_labels)
        self.connections_beeswax = Gauge('impala_connections_beeswax', 'Beeswax connections', common_labels)
        
        # IO 指标
        self.bytes_read = Gauge('impala_bytes_read_total', 'Total bytes read', common_labels)
        self.bytes_written = Gauge('impala_bytes_written_total', 'Total bytes written', common_labels)
        
        # 准入控制指标
        self.admission_queued = Gauge('impala_admission_queued', 'Queued queries in admission control', common_labels + ['pool'])
        self.admission_running = Gauge('impala_admission_running', 'Running queries in admission control', common_labels + ['pool'])
        
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
            self._process_jvm_metrics(all_metrics.get('jvm'), host_labels)
            self._process_memory_metrics(all_metrics.get('memory'), host_labels)
            self._process_system_metrics(all_metrics.get('system'), host_labels)
            self._process_query_metrics(all_metrics.get('queries'), host_labels)
            self._process_admission_metrics(all_metrics.get('admission'), host_labels)
            
            logger.info("Metrics collected successfully")
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    def _process_jvm_metrics(self, jvm_data: Optional[Dict], host_labels: Dict[str, str]):
        """处理 JVM 指标"""
        if not jvm_data:
            logger.warning("No JVM metrics available")
            return
        
        heap_used = self._extract_value(jvm_data, ['HeapMemoryUsage.used', 'jvm.heap.current-usage-bytes'])
        heap_max = self._extract_value(jvm_data, ['HeapMemoryUsage.max', 'jvm.heap.max-usage-bytes'])
        heap_committed = self._extract_value(jvm_data, ['HeapMemoryUsage.committed', 'jvm.heap.committed-usage-bytes'])
        
        if heap_used is not None:
            self.jvm_heap_used.labels(**host_labels).set(heap_used)
        if heap_max is not None:
            self.jvm_heap_max.labels(**host_labels).set(heap_max)
        if heap_committed is not None:
            self.jvm_heap_committed.labels(**host_labels).set(heap_committed)
        
        non_heap_used = self._extract_value(jvm_data, ['NonHeapMemoryUsage.used', 'jvm.non-heap.current-usage-bytes'])
        if non_heap_used is not None:
            self.jvm_non_heap_used.labels(**host_labels).set(non_heap_used)
        
        gc_count = self._extract_value(jvm_data, ['jvm.gc_count', 'CollectionCount'])
        gc_time = self._extract_value(jvm_data, ['jvm.gc_time_millis', 'CollectionTime'])
        
        if gc_count is not None:
            self.jvm_gc_count.labels(**host_labels).set(gc_count)
        if gc_time is not None:
            self.jvm_gc_time.labels(**host_labels).set(gc_time / 1000.0 if gc_time > 1000 else gc_time)
    
    def _process_memory_metrics(self, memory_data: Optional[Dict], host_labels: Dict[str, str]):
        """处理内存指标"""
        if not memory_data:
            logger.warning("No memory metrics available")
            return
        
        rss = self._extract_value(memory_data, ['memory.rss'])
        if rss is not None:
            self.memory_rss.labels(**host_labels).set(rss)
        
        mapped = self._extract_value(memory_data, ['memory.mapped-bytes'])
        if mapped is not None:
            self.memory_mapped.labels(**host_labels).set(mapped)
        
        total_used = self._extract_value(memory_data, ['memory.total-used'])
        if total_used is not None:
            self.memory_total_used.labels(**host_labels).set(total_used)
        
        tcmalloc_in_use = self._extract_value(memory_data, ['tcmalloc.bytes-in-use'])
        tcmalloc_reserved = self._extract_value(memory_data, ['tcmalloc.total-bytes-reserved'])
        
        if tcmalloc_in_use is not None:
            self.tcmalloc_in_use.labels(**host_labels).set(tcmalloc_in_use)
        if tcmalloc_reserved is not None:
            self.tcmalloc_reserved.labels(**host_labels).set(tcmalloc_reserved)
        
        bp_limit = self._extract_value(memory_data, ['buffer-pool.limit'])
        bp_reserved = self._extract_value(memory_data, ['buffer-pool.reserved'])
        bp_allocated = self._extract_value(memory_data, ['buffer-pool.system-allocated'])
        
        if bp_limit is not None:
            self.buffer_pool_limit.labels(**host_labels).set(bp_limit)
        if bp_reserved is not None:
            self.buffer_pool_reserved.labels(**host_labels).set(bp_reserved)
        if bp_allocated is not None:
            self.buffer_pool_allocated.labels(**host_labels).set(bp_allocated)
    
    def _process_system_metrics(self, system_data: Optional[Dict], host_labels: Dict[str, str]):
        """处理系统资源指标"""
        if not system_data:
            logger.warning("No system metrics available")
            return
        
        threads_running = self._extract_value(system_data, ['thread-manager.running-threads'])
        threads_created = self._extract_value(system_data, ['thread-manager.total-threads-created'])
        
        if threads_running is not None:
            self.threads_running.labels(**host_labels).set(threads_running)
        if threads_created is not None:
            self.threads_created.labels(**host_labels).set(threads_created)
        
        hs2_conn = self._extract_value(system_data, ['impala.thrift-server.hiveserver2-frontend.connections-in-use'])
        beeswax_conn = self._extract_value(system_data, ['impala.thrift-server.beeswax-frontend.connections-in-use'])
        
        if hs2_conn is not None:
            self.connections_hiveserver2.labels(**host_labels).set(hs2_conn)
        if beeswax_conn is not None:
            self.connections_beeswax.labels(**host_labels).set(beeswax_conn)
        
        bytes_read = self._extract_value(system_data, ['impala-server.io-mgr.bytes-read'])
        bytes_written = self._extract_value(system_data, ['impala-server.io-mgr.bytes-written'])
        
        if bytes_read is not None:
            self.bytes_read.labels(**host_labels).set(bytes_read)
        if bytes_written is not None:
            self.bytes_written.labels(**host_labels).set(bytes_written)
    
    def _process_query_metrics(self, query_data: Optional[Dict], host_labels: Dict[str, str]):
        """处理查询指标 - 设置为瞬时值"""
        if not query_data:
            logger.warning("No query metrics available")
            return
        
        current_states = query_data.get('current_states', {})
        
        # 设置当前查询状态（瞬时值）
        self.queries_running.labels(**host_labels).set(current_states.get('running', 0))
        self.queries_waiting.labels(**host_labels).set(current_states.get('waiting', 0))
        self.queries_executing.labels(**host_labels).set(current_states.get('executing', 0))
        self.queries_finished.labels(**host_labels).set(current_states.get('finished', 0))
        self.queries_exception.labels(**host_labels).set(current_states.get('exception', 0))
        self.queries_cancelled.labels(**host_labels).set(current_states.get('cancelled', 0))
        
        in_flight_count = query_data.get('in_flight_count', 0)
        self.queries_in_flight.labels(**host_labels).set(in_flight_count)
    
    def _process_admission_metrics(self, admission_data: Optional[Dict], host_labels: Dict[str, str]):
        """处理准入控制指标"""
        if not admission_data:
            return
        
        for key, value in admission_data.items():
            if 'local-num-queued' in key:
                pool_name = self._extract_pool_name(key)
                self.admission_queued.labels(pool=pool_name, **host_labels).set(value)
            elif 'agg-num-running' in key:
                pool_name = self._extract_pool_name(key)
                self.admission_running.labels(pool=pool_name, **host_labels).set(value)
    
    def _extract_value(self, data: Dict, keys: list) -> Optional[float]:
        """从数据中提取数值"""
        if not data:
            return None
        
        for key in keys:
            if key in data:
                value = data[key]
                if isinstance(value, (int, float)):
                    return float(value)
                elif isinstance(value, str):
                    return self._parse_value_string(value)
        return None
    
    def _parse_value_string(self, value_str: str) -> Optional[float]:
        """解析数值字符串"""
        if not value_str or value_str == 'N/A':
            return None
        
        value_str = value_str.replace(',', '').strip()
        
        multipliers = {
            'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4,
            'K': 1000, 'M': 1000**2, 'G': 1000**3, 'T': 1000**4
        }
        
        for unit, multiplier in multipliers.items():
            if value_str.endswith(unit):
                try:
                    number = float(value_str[:-len(unit)].strip())
                    return number * multiplier
                except ValueError:
                    continue
        
        try:
            return float(value_str)
        except ValueError:
            return None
    
    def _extract_pool_name(self, key: str) -> str:
        """从指标名称中提取资源池名称"""
        parts = key.split('.')
        return parts[-1] if parts else 'default'
    
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
