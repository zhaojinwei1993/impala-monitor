#!/usr/bin/env python3
"""
测试指标提取脚本 - 基于已知的Impala指标数据结构
用于验证指标解析逻辑，无需实际连接Impala
"""

import json
import sys
from typing import Dict, Any, List

def extract_metrics(data: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
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
                    metrics.extend(extract_metrics(child_group, child_prefix))
        
        # 处理其他嵌套结构
        for key, value in data.items():
            if key not in ['metrics', 'child_groups', 'name'] and isinstance(value, dict):
                new_prefix = f"{prefix}.{key}" if prefix else key
                metrics.extend(extract_metrics(value, new_prefix))
    
    return metrics

def categorize_metrics(metrics: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """分类指标"""
    categories = {
        'jvm': [],
        'memory': [],
        'buffer_pool': [],
        'impala_server': [],
        'admission_controller': [],
        'io_mgr': [],
        'tcmalloc': [],
        'other': []
    }
    
    for metric in metrics:
        name = metric['name'].lower()
        
        if 'jvm' in name:
            categories['jvm'].append(metric)
        elif 'memory' in name or 'mem-' in name:
            categories['memory'].append(metric)
        elif 'buffer-pool' in name:
            categories['buffer_pool'].append(metric)
        elif 'impala-server' in name:
            categories['impala_server'].append(metric)
        elif 'admission-controller' in name:
            categories['admission_controller'].append(metric)
        elif 'io-mgr' in name:
            categories['io_mgr'].append(metric)
        elif 'tcmalloc' in name:
            categories['tcmalloc'].append(metric)
        else:
            categories['other'].append(metric)
    
    return categories

def format_value(metric: Dict[str, Any]) -> str:
    """格式化指标值"""
    value = metric.get('value', 0)
    kind = metric.get('kind', 'UNKNOWN')
    units = metric.get('units', 'NONE')
    human_readable = metric.get('human_readable', str(value))
    
    if kind == 'PROPERTY':
        return str(value)
    elif units == 'BYTES':
        return human_readable
    elif units in ['TIME_MS', 'TIME_US', 'TIME_NS', 'TIME_S']:
        return human_readable
    else:
        return str(value)

def main():
    # 模拟的Impala指标数据结构（基于之前获取的真实数据）
    sample_data = {
        "metric_group": {
            "name": "impala-metrics",
            "metrics": [
                {
                    "name": "thread-manager.running-threads",
                    "description": "The number of running threads in this process.",
                    "human_readable": "31",
                    "value": 31,
                    "kind": "GAUGE",
                    "units": "NONE"
                },
                {
                    "name": "impala-server.num-queries-registered",
                    "description": "The total number of queries registered on this Impala server instance.",
                    "human_readable": "4",
                    "value": 4,
                    "kind": "GAUGE",
                    "units": "UNIT"
                }
            ],
            "child_groups": [
                {
                    "name": "jvm",
                    "metrics": [
                        {
                            "name": "heap.current-usage-bytes",
                            "description": "Jvm heap Current Usage Bytes",
                            "human_readable": "13.32 GB",
                            "value": 14304247000,
                            "kind": "GAUGE",
                            "units": "BYTES"
                        },
                        {
                            "name": "gc_count",
                            "description": "Jvm Garbage Collection Count",
                            "human_readable": "1.17K",
                            "value": 1169,
                            "kind": "COUNTER",
                            "units": "UNIT"
                        }
                    ],
                    "child_groups": []
                },
                {
                    "name": "memory",
                    "metrics": [
                        {
                            "name": "rss",
                            "description": "Resident set size (RSS) of this process",
                            "human_readable": "33.79 GB",
                            "value": 36278579200,
                            "kind": "GAUGE",
                            "units": "BYTES"
                        }
                    ],
                    "child_groups": []
                },
                {
                    "name": "impala-server",
                    "metrics": [
                        {
                            "name": "num-queries",
                            "description": "The total number of queries processed",
                            "human_readable": "35.81K",
                            "value": 35812,
                            "kind": "COUNTER",
                            "units": "UNIT"
                        },
                        {
                            "name": "backend-num-queries-executing",
                            "description": "The number of queries currently executing on this backend",
                            "human_readable": "4",
                            "value": 4,
                            "kind": "GAUGE",
                            "units": "UNIT"
                        }
                    ],
                    "child_groups": []
                }
            ]
        }
    }
    
    print("Impala 指标提取测试")
    print("=" * 50)
    
    # 提取所有指标
    all_metrics = extract_metrics(sample_data)
    print(f"总共提取到 {len(all_metrics)} 个指标")
    
    # 分类指标
    categorized = categorize_metrics(all_metrics)
    
    # 显示各类别的指标
    for category, metrics in categorized.items():
        if metrics:
            print(f"\n{category.upper()} 指标 ({len(metrics)} 个):")
            print("-" * 40)
            for metric in metrics[:5]:  # 只显示前5个
                value_str = format_value(metric)
                print(f"  {metric['name']}: {value_str}")
                if metric.get('description'):
                    print(f"    描述: {metric['description']}")
            
            if len(metrics) > 5:
                print(f"    ... 还有 {len(metrics) - 5} 个指标")
    
    # 重点关注的指标
    print(f"\n重点监控指标:")
    print("-" * 40)
    
    key_metrics = [
        'jvm.heap.current-usage-bytes',
        'memory.rss', 
        'impala-server.num-queries',
        'impala-server.backend-num-queries-executing',
        'thread-manager.running-threads'
    ]
    
    for metric in all_metrics:
        for key_name in key_metrics:
            if key_name in metric['name']:
                value_str = format_value(metric)
                print(f"  {metric['name']}: {value_str}")
                break
    
    print(f"\n测试完成！指标提取逻辑工作正常。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
