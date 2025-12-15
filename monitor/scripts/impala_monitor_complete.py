#!/usr/bin/env python3
"""
完整的Impala监控脚本
支持指标采集、分析和报告
"""

import json
import requests
import time
import sys
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime

class ImpalaMonitor:
    def __init__(self, host: str, port: int = 25000, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        
    def fetch_metrics(self) -> Optional[Dict[str, Any]]:
        """获取Impala指标"""
        try:
            url = f"{self.base_url}/metrics?json"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取指标失败: {e}")
            return None
    
    def extract_metrics(self, data: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
        """递归提取指标"""
        metrics = []
        
        if isinstance(data, dict):
            # 处理metrics数组
            if 'metrics' in data and isinstance(data['metrics'], list):
                for metric in data['metrics']:
                    if isinstance(metric, dict) and 'name' in metric:
                        metric_name = f"{prefix}.{metric['name']}" if prefix else metric['name']
                        metrics.append({
                            'name': metric_name,
                            'value': metric.get('value', 0),
                            'kind': metric.get('kind', 'UNKNOWN'),
                            'units': metric.get('units', 'NONE'),
                            'description': metric.get('description', ''),
                            'human_readable': metric.get('human_readable', str(metric.get('value', 0)))
                        })
            
            # 处理child_groups
            if 'child_groups' in data and isinstance(data['child_groups'], list):
                for child_group in data['child_groups']:
                    if isinstance(child_group, dict) and 'name' in child_group:
                        child_prefix = f"{prefix}.{child_group['name']}" if prefix else child_group['name']
                        metrics.extend(self.extract_metrics(child_group, child_prefix))
            
            # 处理其他嵌套结构
            for key, value in data.items():
                if key not in ['metrics', 'child_groups', 'name'] and isinstance(value, dict):
                    new_prefix = f"{prefix}.{key}" if prefix else key
                    metrics.extend(self.extract_metrics(value, new_prefix))
        
        return metrics
    
    def get_key_metrics(self, all_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取关键指标"""
        key_metrics = {}
        
        # 定义关键指标映射
        key_patterns = {
            'jvm_heap_used': ['jvm.heap.current-usage-bytes'],
            'jvm_heap_max': ['jvm.heap.max-usage-bytes'],
            'memory_rss': ['memory.rss'],
            'queries_registered': ['impala-server.num-queries-registered'],
            'queries_executing': ['impala-server.backend-num-queries-executing'],
            'queries_total': ['impala-server.num-queries'],
            'threads_running': ['thread-manager.running-threads'],
            'gc_count': ['jvm.gc_count'],
            'gc_time': ['jvm.gc_time_millis'],
            'tcmalloc_used': ['tcmalloc.bytes-in-use'],
            'buffer_pool_used': ['buffer-pool.system-allocated']
        }
        
        for metric in all_metrics:
            metric_name = metric['name'].lower()
            
            for key_name, patterns in key_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in metric_name:
                        key_metrics[key_name] = {
                            'value': metric['value'],
                            'human_readable': metric['human_readable'],
                            'units': metric['units']
                        }
                        break
        
        return key_metrics
    
    def analyze_health(self, key_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """分析系统健康状况"""
        health = {
            'status': 'healthy',
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # JVM堆内存检查
        if 'jvm_heap_used' in key_metrics and 'jvm_heap_max' in key_metrics:
            heap_used = key_metrics['jvm_heap_used']['value']
            heap_max = key_metrics['jvm_heap_max']['value']
            
            if heap_max > 0:
                heap_usage_pct = (heap_used / heap_max) * 100
                
                if heap_usage_pct > 90:
                    health['errors'].append(f"JVM堆内存使用率过高: {heap_usage_pct:.1f}%")
                    health['recommendations'].append("考虑增加JVM堆内存或优化查询")
                    health['status'] = 'critical'
                elif heap_usage_pct > 80:
                    health['warnings'].append(f"JVM堆内存使用率较高: {heap_usage_pct:.1f}%")
                    health['recommendations'].append("监控内存使用趋势")
                    if health['status'] == 'healthy':
                        health['status'] = 'warning'
        
        # 查询数量检查
        if 'queries_executing' in key_metrics:
            executing = key_metrics['queries_executing']['value']
            
            if executing > 50:
                health['warnings'].append(f"执行中查询数量较多: {executing}")
                health['recommendations'].append("检查是否有长时间运行的查询")
                if health['status'] == 'healthy':
                    health['status'] = 'warning'
        
        # GC检查
        if 'gc_time' in key_metrics:
            gc_time = key_metrics['gc_time']['value']
            
            if gc_time > 300000:  # 5分钟
                health['warnings'].append(f"GC时间较长: {gc_time/1000:.1f}秒")
                health['recommendations'].append("检查JVM GC配置和内存使用")
                if health['status'] == 'healthy':
                    health['status'] = 'warning'
        
        return health
    
    def generate_report(self, key_metrics: Dict[str, Any], health: Dict[str, Any]) -> str:
        """生成监控报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
Impala 监控报告
=====================================
时间: {timestamp}
主机: {self.host}:{self.port}
状态: {health['status'].upper()}

关键指标:
-------------------------------------"""
        
        # 内存相关
        if 'memory_rss' in key_metrics:
            report += f"\n• 进程内存(RSS): {key_metrics['memory_rss']['human_readable']}"
        
        if 'jvm_heap_used' in key_metrics:
            report += f"\n• JVM堆内存: {key_metrics['jvm_heap_used']['human_readable']}"
        
        if 'tcmalloc_used' in key_metrics:
            report += f"\n• TCMalloc使用: {key_metrics['tcmalloc_used']['human_readable']}"
        
        # 查询相关
        if 'queries_executing' in key_metrics:
            report += f"\n• 执行中查询: {key_metrics['queries_executing']['value']}"
        
        if 'queries_registered' in key_metrics:
            report += f"\n• 注册查询数: {key_metrics['queries_registered']['value']}"
        
        if 'queries_total' in key_metrics:
            report += f"\n• 总查询数: {key_metrics['queries_total']['human_readable']}"
        
        # 系统相关
        if 'threads_running' in key_metrics:
            report += f"\n• 运行线程数: {key_metrics['threads_running']['value']}"
        
        if 'gc_count' in key_metrics:
            report += f"\n• GC次数: {key_metrics['gc_count']['human_readable']}"
        
        # 健康状况
        if health['warnings'] or health['errors']:
            report += f"\n\n健康状况:"
            report += f"\n-------------------------------------"
            
            for error in health['errors']:
                report += f"\n❌ {error}"
            
            for warning in health['warnings']:
                report += f"\n⚠️  {warning}"
            
            if health['recommendations']:
                report += f"\n\n建议:"
                report += f"\n-------------------------------------"
                for rec in health['recommendations']:
                    report += f"\n• {rec}"
        else:
            report += f"\n\n✅ 系统运行正常"
        
        return report
    
    def monitor_once(self) -> bool:
        """执行一次监控"""
        print(f"正在监控 {self.host}:{self.port}...")
        
        # 获取指标
        raw_data = self.fetch_metrics()
        if not raw_data:
            return False
        
        # 提取指标
        all_metrics = self.extract_metrics(raw_data)
        print(f"提取到 {len(all_metrics)} 个指标")
        
        # 获取关键指标
        key_metrics = self.get_key_metrics(all_metrics)
        
        # 分析健康状况
        health = self.analyze_health(key_metrics)
        
        # 生成报告
        report = self.generate_report(key_metrics, health)
        print(report)
        
        return True
    
    def monitor_continuous(self, interval: int = 60, max_iterations: int = 0):
        """持续监控"""
        iteration = 0
        
        print(f"开始持续监控，间隔 {interval} 秒")
        print("按 Ctrl+C 停止监控")
        
        try:
            while True:
                iteration += 1
                
                print(f"\n{'='*50}")
                print(f"监控轮次 #{iteration}")
                
                success = self.monitor_once()
                
                if not success:
                    print("监控失败，等待下次尝试...")
                
                if max_iterations > 0 and iteration >= max_iterations:
                    print(f"达到最大监控次数 {max_iterations}，退出")
                    break
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n监控已停止 (共执行 {iteration} 次)")

def main():
    parser = argparse.ArgumentParser(description='Impala监控工具')
    parser.add_argument('host', help='Impala主机地址')
    parser.add_argument('--port', type=int, default=25000, help='Impala端口')
    parser.add_argument('--timeout', type=int, default=30, help='请求超时时间(秒)')
    parser.add_argument('--continuous', action='store_true', help='持续监控模式')
    parser.add_argument('--interval', type=int, default=60, help='监控间隔(秒)')
    parser.add_argument('--max-iterations', type=int, default=0, help='最大监控次数(0=无限)')
    
    args = parser.parse_args()
    
    monitor = ImpalaMonitor(args.host, args.port, args.timeout)
    
    if args.continuous:
        monitor.monitor_continuous(args.interval, args.max_iterations)
    else:
        success = monitor.monitor_once()
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
