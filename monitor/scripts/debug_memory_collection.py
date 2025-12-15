#!/usr/bin/env python3
"""
内存采集链路诊断脚本
分析为什么内存指标采集不到值
"""

import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from impala_exporter import ImpalaExporter

def debug_memory_collection(host: str = "10.19.20.149"):
    """调试内存采集链路"""
    
    print(f"🔍 调试内存采集链路: {host}")
    print("=" * 60)
    
    # 1. 创建导出器
    exporter = ImpalaExporter(host)
    
    # 2. 测试连接
    print("1. 测试连接...")
    if not exporter.test_connection():
        print("❌ 连接失败")
        return False
    print("✅ 连接成功")
    
    # 3. 获取原始metrics数据
    print("\n2. 获取原始metrics数据...")
    raw_metrics = exporter._get_metrics_data()
    if not raw_metrics:
        print("❌ 无法获取metrics数据")
        return False
    
    print(f"✅ 获取到metrics数据，包含 {len(raw_metrics)} 个顶级键")
    
    # 4. 分析数据结构
    print("\n3. 分析数据结构...")
    print("顶级键:")
    for key in raw_metrics.keys():
        print(f"  - {key}")
    
    # 5. 查找内存相关的键
    print("\n4. 查找内存相关指标...")
    memory_keys = []
    jvm_keys = []
    tcmalloc_keys = []
    buffer_pool_keys = []
    
    def search_nested(data, prefix=""):
        """递归搜索嵌套数据"""
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                # 检查内存相关键
                if any(mem_word in key.lower() for mem_word in ['memory', 'mem-', 'rss']):
                    memory_keys.append(full_key)
                elif 'jvm' in key.lower():
                    jvm_keys.append(full_key)
                elif 'tcmalloc' in key.lower():
                    tcmalloc_keys.append(full_key)
                elif 'buffer-pool' in key.lower():
                    buffer_pool_keys.append(full_key)
                
                # 递归搜索
                if isinstance(value, dict):
                    search_nested(value, full_key)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            search_nested(item, f"{full_key}[{i}]")
    
    search_nested(raw_metrics)
    
    print(f"找到内存相关键: {len(memory_keys)} 个")
    for key in memory_keys[:10]:  # 只显示前10个
        print(f"  - {key}")
    if len(memory_keys) > 10:
        print(f"  ... 还有 {len(memory_keys) - 10} 个")
    
    print(f"\n找到JVM相关键: {len(jvm_keys)} 个")
    for key in jvm_keys[:10]:
        print(f"  - {key}")
    if len(jvm_keys) > 10:
        print(f"  ... 还有 {len(jvm_keys) - 10} 个")
    
    print(f"\n找到TCMalloc相关键: {len(tcmalloc_keys)} 个")
    for key in tcmalloc_keys[:5]:
        print(f"  - {key}")
    
    print(f"\n找到Buffer Pool相关键: {len(buffer_pool_keys)} 个")
    for key in buffer_pool_keys[:5]:
        print(f"  - {key}")
    
    # 6. 测试当前的提取方法
    print("\n5. 测试当前的提取方法...")
    
    # 测试JVM指标提取
    jvm_metrics = exporter.get_jvm_metrics()
    print(f"JVM指标提取结果: {jvm_metrics is not None}")
    if jvm_metrics:
        print(f"  包含 {len(jvm_metrics)} 个JVM指标")
        for key, value in list(jvm_metrics.items())[:5]:
            print(f"    {key}: {value}")
    
    # 测试内存指标提取
    memory_metrics = exporter.get_memory_metrics()
    print(f"内存指标提取结果: {memory_metrics is not None}")
    if memory_metrics:
        print(f"  包含 {len(memory_metrics)} 个内存指标")
        for key, value in list(memory_metrics.items())[:5]:
            print(f"    {key}: {value}")
    
    # 7. 查看具体的内存指标值
    print("\n6. 查看具体的内存指标值...")
    
    # 查找特定的内存指标
    target_keys = [
        'memory.rss',
        'jvm.heap.current-usage-bytes',
        'tcmalloc.bytes-in-use',
        'buffer-pool.limit'
    ]
    
    def find_value_in_nested(data, target_key, prefix=""):
        """在嵌套数据中查找特定键的值"""
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                if target_key in full_key:
                    if isinstance(value, dict) and 'value' in value:
                        return value['value']
                    elif isinstance(value, (int, float)):
                        return value
                
                if isinstance(value, dict):
                    result = find_value_in_nested(value, target_key, full_key)
                    if result is not None:
                        return result
        return None
    
    for target_key in target_keys:
        value = find_value_in_nested(raw_metrics, target_key)
        print(f"  {target_key}: {value}")
    
    # 8. 保存调试数据
    print("\n7. 保存调试数据...")
    debug_file = "/tmp/impala_metrics_debug.json"
    with open(debug_file, 'w') as f:
        json.dump(raw_metrics, f, indent=2)
    print(f"原始数据已保存到: {debug_file}")
    
    return True

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "10.19.20.149"
    debug_memory_collection(host)
