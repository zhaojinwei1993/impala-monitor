#!/usr/bin/env python3
"""
模拟Impala内存指标的脚本
用于测试监控系统在无法连接真实Impala时的情况
"""

import json
import time
import random
from datetime import datetime

def generate_memory_metrics():
    """生成模拟的内存指标数据"""
    
    # 基础内存值 (bytes)
    base_tcmalloc_bytes = 3460293000  # 3.22 GB
    base_physical_bytes = 4154859520  # 3.87 GB
    base_jvm_heap = 1073741824       # 1 GB
    
    # 添加一些随机变化 (±10%)
    variation = 0.1
    
    tcmalloc_bytes = int(base_tcmalloc_bytes * (1 + random.uniform(-variation, variation)))
    physical_bytes = int(base_physical_bytes * (1 + random.uniform(-variation, variation)))
    jvm_heap_used = int(base_jvm_heap * random.uniform(0.3, 0.8))  # 30-80% 使用率
    jvm_heap_max = base_jvm_heap
    
    # 模拟指标数据结构
    metrics_data = {
        "__common__": {
            "process-name": "impalad",
            "timestamp": datetime.now().isoformat()
        },
        "metric_group": {
            "name": "impala-metrics",
            "metrics": [],
            "child_groups": [
                {
                    "name": "tcmalloc",
                    "metrics": [
                        {
                            "name": "tcmalloc.bytes-in-use",
                            "description": "Number of bytes used by the application",
                            "human_readable": f"{tcmalloc_bytes / (1024**3):.2f} GB",
                            "value": tcmalloc_bytes,
                            "kind": "GAUGE",
                            "units": "BYTES"
                        },
                        {
                            "name": "tcmalloc.physical-bytes-reserved",
                            "description": "Physical memory used by the process",
                            "human_readable": f"{physical_bytes / (1024**3):.2f} GB",
                            "value": physical_bytes,
                            "kind": "GAUGE",
                            "units": "BYTES"
                        }
                    ]
                },
                {
                    "name": "jvm",
                    "metrics": [
                        {
                            "name": "jvm.heap.used",
                            "description": "JVM heap memory used",
                            "human_readable": f"{jvm_heap_used / (1024**2):.0f} MB",
                            "value": jvm_heap_used,
                            "kind": "GAUGE",
                            "units": "BYTES"
                        },
                        {
                            "name": "jvm.heap.max",
                            "description": "JVM heap memory maximum",
                            "human_readable": f"{jvm_heap_max / (1024**2):.0f} MB",
                            "value": jvm_heap_max,
                            "kind": "GAUGE",
                            "units": "BYTES"
                        }
                    ]
                }
            ]
        }
    }
    
    return metrics_data

def generate_queries_data():
    """生成模拟的查询数据"""
    
    # 模拟一些查询
    queries = []
    query_states = ["RUNNING", "FINISHED", "PENDING"]
    
    for i in range(random.randint(1, 5)):
        query = {
            "query_id": f"query_{i}_{int(time.time())}",
            "user": f"user_{random.randint(1, 3)}",
            "state": random.choice(query_states),
            "sql": f"SELECT * FROM table_{i} WHERE id > {random.randint(1, 1000)}",
            "memory_usage": random.randint(100*1024*1024, 2*1024*1024*1024),  # 100MB - 2GB
            "duration_ms": random.randint(1000, 300000)  # 1s - 5min
        }
        queries.append(query)
    
    return {"queries": queries}

def print_metrics_summary(metrics_data):
    """打印指标摘要"""
    print("🔍 模拟内存指标生成成功")
    print("=" * 60)
    
    # 提取tcmalloc指标
    for group in metrics_data["metric_group"]["child_groups"]:
        if group["name"] == "tcmalloc":
            for metric in group["metrics"]:
                if metric["name"] == "tcmalloc.bytes-in-use":
                    print(f"TCMalloc 使用内存: {metric['human_readable']}")
                elif metric["name"] == "tcmalloc.physical-bytes-reserved":
                    print(f"物理内存占用: {metric['human_readable']}")
        elif group["name"] == "jvm":
            heap_used = None
            heap_max = None
            for metric in group["metrics"]:
                if metric["name"] == "jvm.heap.used":
                    heap_used = metric["value"]
                elif metric["name"] == "jvm.heap.max":
                    heap_max = metric["value"]
            
            if heap_used and heap_max:
                usage_percent = (heap_used / heap_max) * 100
                print(f"JVM 堆内存: {heap_used/(1024**2):.0f}MB / {heap_max/(1024**2):.0f}MB ({usage_percent:.1f}%)")

def main():
    """主函数"""
    print("🚀 启动Impala内存指标模拟器")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 生成指标数据
    metrics_data = generate_memory_metrics()
    queries_data = generate_queries_data()
    
    # 打印摘要
    print_metrics_summary(metrics_data)
    print()
    
    # 保存到文件
    output_file = "/Users/zhaojinwei/impala-monitor/simulated_metrics.json"
    with open(output_file, 'w') as f:
        json.dump({
            "metrics": metrics_data,
            "queries": queries_data,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"📁 数据已保存到: {output_file}")
    print()
    
    # 显示关键指标值
    print("📊 关键指标值:")
    print("-" * 40)
    for group in metrics_data["metric_group"]["child_groups"]:
        if group["name"] == "tcmalloc":
            for metric in group["metrics"]:
                if "bytes-in-use" in metric["name"]:
                    print(f"memory.rss = {metric['value']}")
                elif "physical-bytes-reserved" in metric["name"]:
                    print(f"memory.physical = {metric['value']}")
        elif group["name"] == "jvm":
            for metric in group["metrics"]:
                if "heap.used" in metric["name"]:
                    print(f"jvm.heap.used = {metric['value']}")
                elif "heap.max" in metric["name"]:
                    print(f"jvm.heap.max = {metric['value']}")
    
    print()
    print("✅ 模拟数据生成完成！")
    print("💡 可以使用这些数据来测试监控系统的指标解析功能")

if __name__ == "__main__":
    main()
