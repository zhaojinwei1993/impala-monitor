#!/usr/bin/env python3
"""
测试 Impala Monitor
验证指标采集和主机标签功能
"""

import sys
import os
import time
import requests
import logging

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from impala_exporter import ImpalaExporter
from impala_monitor import ImpalaMonitor, get_local_ip, get_hostname

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_exporter(host='localhost', port=25000):
    """测试 Impala 导出器"""
    logger.info(f"Testing Impala Exporter for {host}:{port}")
    
    exporter = ImpalaExporter(host, port)
    
    # 测试连接
    if not exporter.test_connection():
        logger.error("Cannot connect to Impala")
        return False
    
    logger.info("✓ Connection successful")
    
    # 测试各类指标
    all_metrics = exporter.get_all_metrics()
    
    for metric_type, data in all_metrics.items():
        if data:
            logger.info(f"✓ {metric_type} metrics: {len(data)} items")
            # 显示前几个指标
            if isinstance(data, dict):
                for i, (key, value) in enumerate(data.items()):
                    if i < 3:  # 只显示前3个
                        logger.info(f"  - {key}: {value}")
                    elif i == 3:
                        logger.info(f"  - ... and {len(data)-3} more")
                        break
        else:
            logger.warning(f"✗ {metric_type} metrics: No data")
    
    return True


def test_monitor(host='localhost', port=25000):
    """测试 Monitor"""
    logger.info(f"Testing Impala Monitor for {host}:{port}")
    
    config = {
        'impala_host': host,
        'impala_port': port,
        'metrics_port': 9357,  # 使用不同端口避免冲突
        'collect_interval': 10
    }
    
    monitor = ImpalaMonitor(config)
    
    # 显示主机信息
    logger.info(f"Host IP: {monitor.host_ip}")
    logger.info(f"Hostname: {monitor.hostname}")
    
    # 启动服务器
    monitor.start_server()
    
    # 采集一次指标
    monitor.collect_metrics()
    
    # 等待一下让指标生效
    time.sleep(2)
    
    # 检查 Prometheus 指标
    try:
        response = requests.get(f"http://localhost:{config['metrics_port']}/metrics")
        if response.status_code == 200:
            metrics_text = response.text
            
            # 检查是否包含主机标签
            if f'host_ip="{monitor.host_ip}"' in metrics_text:
                logger.info("✓ Host IP label found in metrics")
            else:
                logger.warning("✗ Host IP label not found in metrics")
            
            if f'hostname="{monitor.hostname}"' in metrics_text:
                logger.info("✓ Hostname label found in metrics")
            else:
                logger.warning("✗ Hostname label not found in metrics")
            
            # 统计指标数量
            metric_lines = [line for line in metrics_text.split('\n') 
                          if line and not line.startswith('#')]
            logger.info(f"✓ Total metrics exported: {len(metric_lines)}")
            
            # 显示一些示例指标
            logger.info("Sample metrics:")
            for i, line in enumerate(metric_lines[:5]):
                logger.info(f"  {line}")
            
            return True
        else:
            logger.error(f"Failed to get metrics: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking metrics: {e}")
        return False


def main():
    """主测试函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Impala Monitor')
    parser.add_argument('--host', default='localhost', help='Impala host')
    parser.add_argument('--port', type=int, default=25000, help='Impala port')
    parser.add_argument('--test-exporter', action='store_true', help='Test exporter only')
    parser.add_argument('--test-monitor', action='store_true', help='Test monitor only')
    
    args = parser.parse_args()
    
    if not args.test_exporter and not args.test_monitor:
        # 默认测试所有
        args.test_exporter = True
        args.test_monitor = True
    
    logger.info("=" * 50)
    logger.info("Impala Monitor Test Suite")
    logger.info("=" * 50)
    
    success = True
    
    if args.test_exporter:
        logger.info("\n1. Testing Impala Exporter...")
        if not test_exporter(args.host, args.port):
            success = False
    
    if args.test_monitor:
        logger.info("\n2. Testing Impala Monitor...")
        if not test_monitor(args.host, args.port):
            success = False
    
    logger.info("\n" + "=" * 50)
    if success:
        logger.info("✓ All tests passed!")
    else:
        logger.error("✗ Some tests failed!")
    logger.info("=" * 50)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
