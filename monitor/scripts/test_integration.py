#!/usr/bin/env python3
"""
完整集成测试 - 使用真实metrics数据测试监控系统
"""

import json
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from impala_exporter import ImpalaExporter

def test_integration():
    """完整集成测试"""
    
    print("🚀 Impala监控系统集成测试")
    print("=" * 50)
    
    # 读取真实metrics数据
    metrics_file = "/Users/zhaojinwei/impala-monitor/test_data/metrics.json"
    
    if not os.path.exists(metrics_file):
        print(f"❌ 文件不存在: {metrics_file}")
        return False
    
    try:
        with open(metrics_file, 'r') as f:
            real_data = json.load(f)
        
        # 创建exporter实例
        exporter = ImpalaExporter("10.19.20.149")  # 使用真实主机
        
        print("📊 测试内存指标解析:")
        memory_metrics = exporter.parse_memory_metrics(real_data)
        
        # 显示关键指标
        key_metrics = {
            'TCMalloc使用': memory_metrics.get('tcmalloc_bytes_in_use', 0),
            'TCMalloc物理': memory_metrics.get('tcmalloc_physical_bytes', 0),
            'RSS内存': memory_metrics.get('memory_rss', 0),
            'JVM堆使用': memory_metrics.get('jvm_heap_used', 0),
            'JVM堆最大': memory_metrics.get('jvm_heap_max', 0)
        }
        
        for name, value in key_metrics.items():
            if value > 0:
                gb_value = value / (1024**3)
                print(f"  ✅ {name}: {gb_value:.2f} GB")
            else:
                print(f"  ❌ {name}: 未获取到数据")
        
        # 计算内存使用率
        if memory_metrics.get('jvm_heap_used') and memory_metrics.get('jvm_heap_max'):
            heap_usage = (memory_metrics['jvm_heap_used'] / memory_metrics['jvm_heap_max']) * 100
            print(f"  📈 JVM堆使用率: {heap_usage:.1f}%")
        
        # 生成Prometheus格式指标示例
        print(f"\n📈 Prometheus指标格式示例:")
        host_ip = "10.19.20.149"
        hostname = "impala-node-1"
        
        prometheus_metrics = []
        for key, value in memory_metrics.items():
            metric_name = f"impala_{key}"
            prometheus_metrics.append(
                f'{metric_name}{{host_ip="{host_ip}",hostname="{hostname}"}} {value}'
            )
        
        for metric in prometheus_metrics[:5]:  # 显示前5个
            print(f"  {metric}")
        
        print(f"\n✅ 成功解析 {len(memory_metrics)} 个内存指标")
        
        # 验证指标完整性
        required_metrics = ['tcmalloc_bytes_in_use', 'memory_rss', 'jvm_heap_used']
        missing = [m for m in required_metrics if m not in memory_metrics or memory_metrics[m] == 0]
        
        if missing:
            print(f"⚠️  缺失关键指标: {missing}")
            return False
        
        print(f"🎉 集成测试通过! 监控系统可以正确解析真实Impala指标")
        return True
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
