#!/usr/bin/env python3
"""
测试真实metrics.json解析
"""

import json
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from impala_exporter import ImpalaExporter

def test_real_metrics_parsing():
    """测试真实metrics数据解析"""
    
    # 读取真实metrics数据
    metrics_file = "/Users/zhaojinwei/impala-monitor/test_data/metrics.json"
    
    if not os.path.exists(metrics_file):
        print(f"❌ 文件不存在: {metrics_file}")
        return False
    
    try:
        with open(metrics_file, 'r') as f:
            real_data = json.load(f)
        
        print("📊 测试真实metrics解析")
        print("=" * 40)
        
        # 创建exporter实例
        exporter = ImpalaExporter("dummy")  # host不重要，只测试解析
        
        # 解析内存指标
        memory_metrics = exporter.parse_memory_metrics(real_data)
        
        print("🧠 解析到的内存指标:")
        for key, value in memory_metrics.items():
            if isinstance(value, (int, float)):
                # 转换为可读格式
                if value > 1024**3:  # GB
                    readable = f"{value / 1024**3:.2f} GB"
                elif value > 1024**2:  # MB
                    readable = f"{value / 1024**2:.2f} MB"
                elif value > 1024:  # KB
                    readable = f"{value / 1024:.2f} KB"
                else:
                    readable = f"{value} bytes"
                print(f"  ✅ {key}: {readable} ({value})")
            else:
                print(f"  ✅ {key}: {value}")
        
        # 验证关键指标
        expected_metrics = [
            'tcmalloc_bytes_in_use',
            'tcmalloc_physical_bytes', 
            'memory_rss',
            'jvm_heap_used',
            'jvm_heap_max'
        ]
        
        print(f"\n🔍 验证关键指标:")
        missing_metrics = []
        for metric in expected_metrics:
            if metric in memory_metrics:
                print(f"  ✅ {metric}: 已找到")
            else:
                print(f"  ❌ {metric}: 缺失")
                missing_metrics.append(metric)
        
        if missing_metrics:
            print(f"\n⚠️  缺失指标: {missing_metrics}")
            print("需要检查指标名称或JSON结构")
            return False
        else:
            print(f"\n🎉 所有关键指标解析成功!")
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_metrics_parsing()
    sys.exit(0 if success else 1)
