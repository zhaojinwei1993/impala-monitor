#!/usr/bin/env python3
"""
测试脚本：验证JMX代码已移除
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from impala_exporter import ImpalaExporter

def test_no_jmx():
    """测试确认JMX相关代码已移除"""
    
    # 创建导出器实例
    exporter = ImpalaExporter("10.19.20.149")
    
    # 检查是否还有jmx_url属性
    if hasattr(exporter, 'jmx_url'):
        print("❌ 错误: 仍然存在 jmx_url 属性")
        return False
    
    # 检查是否还有_get_jmx_data方法
    if hasattr(exporter, '_get_jmx_data'):
        print("❌ 错误: 仍然存在 _get_jmx_data 方法")
        return False
    
    # 检查必要的属性是否存在
    required_attrs = ['metrics_url', 'queries_url', 'host', 'port']
    for attr in required_attrs:
        if not hasattr(exporter, attr):
            print(f"❌ 错误: 缺少必要属性 {attr}")
            return False
    
    print("✅ JMX代码已成功移除")
    print(f"✅ metrics_url: {exporter.metrics_url}")
    print(f"✅ queries_url: {exporter.queries_url}")
    
    return True

if __name__ == "__main__":
    success = test_no_jmx()
    sys.exit(0 if success else 1)
