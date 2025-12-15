#!/usr/bin/env python3
"""
探索Impala实际可用的指标
"""

import requests
import json
import sys

def explore_metrics(host, port=25000):
    """探索指标"""
    url = f"http://{host}:{port}/metrics?json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"从 {url} 获取数据")
        print("=" * 80)
        
        # 分析数据结构
        print(f"顶层数据结构: {type(data)}")
        if isinstance(data, dict):
            print(f"顶层键: {list(data.keys())}")
        
        # 提取所有指标
        all_metrics = []
        
        def extract_metrics(obj, prefix=""):
            """递归提取指标"""
            if isinstance(obj, dict):
                if 'metrics' in obj:
                    # 这是一个指标组
                    for metric in obj['metrics']:
                        if isinstance(metric, dict) and 'name' in metric:
                            name = metric['name']
                            if prefix:
                                name = f"{prefix}.{name}"
                            all_metrics.append((name, metric))
                
                if 'child_groups' in obj:
                    # 处理子组
                    for child in obj['child_groups']:
                        if isinstance(child, dict) and 'name' in child:
                            child_prefix = f"{prefix}.{child['name']}" if prefix else child['name']
                            extract_metrics(child, child_prefix)
                
                # 处理其他字典项
                for key, value in obj.items():
                    if key not in ['metrics', 'child_groups', 'name']:
                        if isinstance(value, (dict, list)):
                            new_prefix = f"{prefix}.{key}" if prefix else key
                            extract_metrics(value, new_prefix)
                        else:
                            name = f"{prefix}.{key}" if prefix else key
                            all_metrics.append((name, {'name': name, 'value': value}))
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_metrics(item, f"{prefix}[{i}]" if prefix else f"[{i}]")
        
        # 提取指标
        extract_metrics(data)
        
        print(f"总共提取到 {len(all_metrics)} 个指标")
        print("=" * 80)
        
        # 分类显示指标
        categories = {
            'jvm': [],
            'memory': [],
            'tcmalloc': [],
            'buffer': [],
            'thread': [],
            'connection': [],
            'query': [],
            'io': [],
            'admission': [],
            'impala-server': [],
            'catalog': [],
            'statestore': []
        }
        
        other_metrics = []
        
        for name, metric_data in all_metrics:
            name_lower = name.lower()
            categorized = False
            
            for category in categories:
                if category in name_lower or category.replace('-', '.') in name_lower:
                    categories[category].append((name, metric_data))
                    categorized = True
                    break
            
            if not categorized:
                other_metrics.append((name, metric_data))
        
        # 显示各类指标
        for category, metrics in categories.items():
            if metrics:
                print(f"\n{category.upper()} 相关指标 ({len(metrics)} 个):")
                print("-" * 40)
                for name, metric_data in metrics[:10]:  # 只显示前10个
                    if isinstance(metric_data, dict):
                        value = metric_data.get('value', metric_data.get('human_readable', 'N/A'))
                        description = metric_data.get('description', '')
                        print(f"  {name}: {value}")
                        if description:
                            print(f"    描述: {description}")
                    else:
                        print(f"  {name}: {metric_data}")
                if len(metrics) > 10:
                    print(f"  ... 还有 {len(metrics)-10} 个")
        
        # 显示其他指标的前20个
        if other_metrics:
            print(f"\n其他指标 ({len(other_metrics)} 个):")
            print("-" * 40)
            for name, metric_data in other_metrics[:20]:
                if isinstance(metric_data, dict):
                    value = metric_data.get('value', metric_data.get('human_readable', 'N/A'))
                    print(f"  {name}: {value}")
                else:
                    print(f"  {name}: {metric_data}")
            if len(other_metrics) > 20:
                print(f"  ... 还有 {len(other_metrics)-20} 个")
        
        return data
        
    except Exception as e:
        print(f"获取指标失败: {e}")
        return None

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("用法: python3 explore_metrics.py <impala_host>")
        sys.exit(1)
    
    host = sys.argv[1]
    explore_metrics(host)
