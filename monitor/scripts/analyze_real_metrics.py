#!/usr/bin/env python3
"""
分析真实的metrics.json文件结构
"""

import json
import sys
import os

def analyze_metrics_structure():
    """分析metrics.json的结构"""
    metrics_file = "/Users/zhaojinwei/impala-monitor/test_data/metrics.json"
    
    if not os.path.exists(metrics_file):
        print(f"❌ 文件不存在: {metrics_file}")
        return
    
    try:
        with open(metrics_file, 'r') as f:
            data = json.load(f)
        
        print("📊 Metrics.json 结构分析")
        print("=" * 50)
        
        # 顶层结构
        print("🔍 顶层键:")
        for key in data.keys():
            print(f"  - {key}")
        
        # 查找内存相关指标
        print("\n🧠 内存相关指标:")
        memory_metrics = find_memory_metrics(data)
        
        for category, metrics in memory_metrics.items():
            print(f"\n📂 {category}:")
            for metric in metrics[:5]:  # 只显示前5个
                print(f"  - {metric['name']}: {metric.get('human_readable', metric.get('value', 'N/A'))}")
            if len(metrics) > 5:
                print(f"  ... 还有 {len(metrics) - 5} 个指标")
        
        # 查找JVM指标
        print("\n☕ JVM相关指标:")
        jvm_metrics = find_jvm_metrics(data)
        for metric in jvm_metrics[:10]:  # 只显示前10个
            print(f"  - {metric['name']}: {metric.get('human_readable', metric.get('value', 'N/A'))}")
        if len(jvm_metrics) > 10:
            print(f"  ... 还有 {len(jvm_metrics) - 10} 个指标")
            
        # 生成采集代码示例
        print("\n💡 建议的采集代码:")
        generate_collection_code(memory_metrics, jvm_metrics)
        
    except Exception as e:
        print(f"❌ 分析文件时出错: {e}")

def find_memory_metrics(data):
    """查找内存相关指标"""
    memory_metrics = {
        'tcmalloc': [],
        'buffer-pool': [],
        'memory': []
    }
    
    def search_metrics(obj, path=""):
        if isinstance(obj, dict):
            # 检查是否是指标组
            if 'name' in obj and 'metrics' in obj:
                group_name = obj['name']
                
                # TCMalloc指标
                if group_name == 'tcmalloc':
                    memory_metrics['tcmalloc'].extend(obj['metrics'])
                
                # Buffer Pool指标
                elif group_name == 'buffer-pool':
                    memory_metrics['buffer-pool'].extend(obj['metrics'])
                
                # Memory指标
                elif group_name == 'memory':
                    memory_metrics['memory'].extend(obj['metrics'])
                
                # 递归搜索子组
                if 'child_groups' in obj:
                    for child in obj['child_groups']:
                        search_metrics(child, f"{path}/{group_name}")
            
            # 递归搜索所有键
            for key, value in obj.items():
                search_metrics(value, f"{path}/{key}")
        
        elif isinstance(obj, list):
            for item in obj:
                search_metrics(item, path)
    
    search_metrics(data)
    return memory_metrics

def find_jvm_metrics(data):
    """查找JVM相关指标"""
    jvm_metrics = []
    
    def search_jvm(obj):
        if isinstance(obj, dict):
            # 检查是否是JVM指标组
            if 'name' in obj and obj['name'] == 'jvm' and 'metrics' in obj:
                jvm_metrics.extend(obj['metrics'])
            
            # 递归搜索
            for value in obj.values():
                search_jvm(value)
        elif isinstance(obj, list):
            for item in obj:
                search_jvm(item)
    
    search_jvm(data)
    return jvm_metrics

def generate_collection_code(memory_metrics, jvm_metrics):
    """生成采集代码示例"""
    print("""
def parse_memory_metrics(self, data):
    \"\"\"解析内存指标\"\"\"
    metrics = {}
    
    def find_metric_group(obj, group_name):
        if isinstance(obj, dict):
            if obj.get('name') == group_name and 'metrics' in obj:
                return obj['metrics']
            if 'child_groups' in obj:
                for child in obj['child_groups']:
                    result = find_metric_group(child, group_name)
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
            if 'bytes-in-use' in name:
                metrics['tcmalloc_bytes_in_use'] = metric.get('value', 0)
            elif 'physical-bytes-reserved' in name:
                metrics['tcmalloc_physical_bytes'] = metric.get('value', 0)
    
    # Memory指标
    memory_metrics = find_metric_group(data, 'memory')
    if memory_metrics:
        for metric in memory_metrics:
            name = metric.get('name', '')
            if name == 'memory.rss':
                metrics['memory_rss'] = metric.get('value', 0)
            elif name == 'memory.total-used':
                metrics['memory_total_used'] = metric.get('value', 0)
    
    # JVM指标
    jvm_metrics = find_metric_group(data, 'jvm')
    if jvm_metrics:
        for metric in jvm_metrics:
            name = metric.get('name', '')
            if 'heap.current-usage-bytes' in name:
                metrics['jvm_heap_used'] = metric.get('value', 0)
            elif 'heap.max-usage-bytes' in name:
                metrics['jvm_heap_max'] = metric.get('value', 0)
    
    return metrics
""")

if __name__ == "__main__":
    analyze_metrics_structure()
