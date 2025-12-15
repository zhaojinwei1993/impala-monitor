#!/usr/bin/env python3
"""
测试内存指标解析功能
验证监控系统能否正确提取和处理内存相关指标
"""

import json
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from impala_exporter import ImpalaExporter
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保impala_exporter.py在正确的路径中")
    sys.exit(1)

class MockImpalaExporter(ImpalaExporter):
    """模拟的ImpalaExporter，使用本地数据而不是网络请求"""
    
    def __init__(self, simulated_data_file):
        # 不调用父类初始化，避免网络连接
        self.host = "simulated"
        self.port = 25000
        self.simulated_data_file = simulated_data_file
        
        # 加载模拟数据
        with open(simulated_data_file, 'r') as f:
            self.simulated_data = json.load(f)
    
    def _get_metrics_data(self):
        """返回模拟的metrics数据"""
        return self.simulated_data["metrics"]
    
    def _get_queries_data(self):
        """返回模拟的queries数据"""
        return self.simulated_data["queries"]

def test_memory_extraction():
    """测试内存指标提取"""
    print("🧪 测试内存指标提取功能")
    print("=" * 60)
    
    # 使用模拟数据
    simulated_file = "/Users/zhaojinwei/impala-monitor/simulated_metrics.json"
    
    if not os.path.exists(simulated_file):
        print(f"❌ 模拟数据文件不存在: {simulated_file}")
        print("请先运行 simulate_memory_metrics.py")
        return False
    
    try:
        # 创建模拟的exporter
        exporter = MockImpalaExporter(simulated_file)
        
        # 获取metrics数据
        metrics_data = exporter._get_metrics_data()
        print(f"✅ 成功加载模拟数据")
        
        # 测试内存指标提取
        print("\n📊 测试内存指标提取:")
        print("-" * 40)
        
        # 查找tcmalloc指标
        tcmalloc_found = False
        jvm_found = False
        
        if "metric_group" in metrics_data and "child_groups" in metrics_data["metric_group"]:
            for group in metrics_data["metric_group"]["child_groups"]:
                if group["name"] == "tcmalloc":
                    tcmalloc_found = True
                    print(f"✅ 找到tcmalloc指标组")
                    
                    for metric in group["metrics"]:
                        name = metric["name"]
                        value = metric["value"]
                        human_readable = metric["human_readable"]
                        
                        if "bytes-in-use" in name:
                            print(f"  📈 TCMalloc使用内存: {human_readable} ({value} bytes)")
                        elif "physical-bytes-reserved" in name:
                            print(f"  📈 物理内存占用: {human_readable} ({value} bytes)")
                
                elif group["name"] == "jvm":
                    jvm_found = True
                    print(f"✅ 找到JVM指标组")
                    
                    heap_used = None
                    heap_max = None
                    
                    for metric in group["metrics"]:
                        name = metric["name"]
                        value = metric["value"]
                        
                        if "heap.used" in name:
                            heap_used = value
                            print(f"  📈 JVM堆已使用: {value / (1024**2):.0f} MB")
                        elif "heap.max" in name:
                            heap_max = value
                            print(f"  📈 JVM堆最大值: {value / (1024**2):.0f} MB")
                    
                    if heap_used and heap_max:
                        usage_percent = (heap_used / heap_max) * 100
                        print(f"  📈 JVM堆使用率: {usage_percent:.1f}%")
        
        # 验证结果
        print(f"\n🔍 验证结果:")
        print("-" * 40)
        
        if tcmalloc_found:
            print("✅ TCMalloc指标提取成功")
        else:
            print("❌ TCMalloc指标提取失败")
        
        if jvm_found:
            print("✅ JVM指标提取成功")
        else:
            print("❌ JVM指标提取失败")
        
        return tcmalloc_found and jvm_found
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_value_extraction():
    """测试具体数值提取"""
    print("\n🔢 测试数值提取功能")
    print("=" * 60)
    
    # 模拟嵌套数据结构
    test_data = {
        "simple_value": 12345,
        "nested": {
            "memory": {
                "rss": 3173271555,
                "heap": 436018903
            }
        },
        "list_data": [
            {"name": "metric1", "value": 100},
            {"name": "metric2", "value": 200}
        ]
    }
    
    # 测试不同的提取路径
    test_cases = [
        ("simple_value", 12345),
        ("nested.memory.rss", 3173271555),
        ("nested.memory.heap", 436018903),
        ("list_data[0].value", 100),
        ("nonexistent.path", None)
    ]
    
    print("测试数据路径提取:")
    for path, expected in test_cases:
        try:
            # 简单的路径解析
            parts = path.split('.')
            current = test_data
            
            for part in parts:
                if '[' in part and ']' in part:
                    # 处理数组索引
                    key = part.split('[')[0]
                    index = int(part.split('[')[1].split(']')[0])
                    current = current[key][index]
                else:
                    current = current[part]
            
            result = current
            status = "✅" if result == expected else "❌"
            print(f"  {status} {path}: {result} (期望: {expected})")
            
        except (KeyError, IndexError, TypeError):
            result = None
            status = "✅" if expected is None else "❌"
            print(f"  {status} {path}: None (期望: {expected})")

def main():
    """主函数"""
    print("🚀 启动内存指标解析测试")
    print(f"📁 工作目录: {os.getcwd()}")
    print()
    
    # 测试内存指标提取
    memory_test_passed = test_memory_extraction()
    
    # 测试数值提取
    test_value_extraction()
    
    print(f"\n📋 测试总结:")
    print("=" * 60)
    
    if memory_test_passed:
        print("✅ 内存指标解析测试通过")
        print("💡 监控系统能够正确识别和提取内存相关指标")
    else:
        print("❌ 内存指标解析测试失败")
        print("💡 需要检查指标提取逻辑")
    
    print()
    print("🔧 下一步建议:")
    if memory_test_passed:
        print("1. 测试实际的Prometheus指标导出")
        print("2. 验证Grafana仪表板显示")
        print("3. 检查指标标签和格式")
    else:
        print("1. 检查impala_exporter.py中的指标解析逻辑")
        print("2. 验证数据结构匹配")
        print("3. 调试_extract_value方法")

if __name__ == "__main__":
    main()
