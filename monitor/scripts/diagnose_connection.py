#!/usr/bin/env python3
"""
Impala 连接诊断脚本
"""

import requests
import socket
import sys
import argparse

def test_tcp_connection(host, port):
    """测试TCP连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"TCP连接测试失败: {e}")
        return False

def test_http_endpoints(host, port):
    """测试HTTP端点"""
    endpoints = [
        f"http://{host}:{port}/",
        f"http://{host}:{port}/metrics",
        f"http://{host}:{port}/metrics?json",
        f"http://{host}:{port}/queries",
        f"http://{host}:{port}/queries?json"
    ]
    
    results = {}
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            results[endpoint] = {
                'status': response.status_code,
                'accessible': True,
                'size': len(response.text)
            }
        except Exception as e:
            results[endpoint] = {
                'status': 'Error',
                'accessible': False,
                'error': str(e)
            }
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Impala连接诊断')
    parser.add_argument('--host', default='localhost', help='Impala主机')
    parser.add_argument('--port', type=int, default=25000, help='Impala端口')
    
    args = parser.parse_args()
    
    print(f"诊断Impala连接: {args.host}:{args.port}")
    print("=" * 50)
    
    # 1. 测试TCP连接
    print("1. TCP连接测试...")
    if test_tcp_connection(args.host, args.port):
        print(f"✓ TCP连接成功: {args.host}:{args.port}")
    else:
        print(f"✗ TCP连接失败: {args.host}:{args.port}")
        print("可能原因:")
        print("- Impala服务未启动")
        print("- 端口被防火墙阻止")
        print("- 网络不通")
        return 1
    
    # 2. 测试HTTP端点
    print("\n2. HTTP端点测试...")
    results = test_http_endpoints(args.host, args.port)
    
    for endpoint, result in results.items():
        if result['accessible']:
            print(f"✓ {endpoint} - HTTP {result['status']} ({result['size']} bytes)")
        else:
            print(f"✗ {endpoint} - {result['error']}")
    
    # 3. 检查关键端点
    print("\n3. 关键端点检查...")
    metrics_endpoint = f"http://{args.host}:{args.port}/metrics?json"
    queries_endpoint = f"http://{args.host}:{args.port}/queries?json"
    
    if results[metrics_endpoint]['accessible']:
        print("✓ metrics端点可访问")
    else:
        print("✗ metrics端点不可访问 - 监控将无法获取指标")
    
    if results[queries_endpoint]['accessible']:
        print("✓ queries端点可访问")
    else:
        print("✗ queries端点不可访问 - 监控将无法获取查询信息")
    
    print("\n诊断完成!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
