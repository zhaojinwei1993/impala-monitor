#!/usr/bin/env python3
"""
Impala连接故障诊断和修复建议脚本
"""

import socket
import requests
import time
import sys
import argparse
from typing import Dict, List, Tuple

def test_tcp_connection(host: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
    """测试TCP连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return True, "TCP连接成功"
        else:
            return False, f"TCP连接失败，错误代码: {result}"
    except Exception as e:
        return False, f"TCP连接异常: {str(e)}"

def test_http_endpoint(url: str, timeout: int = 10) -> Tuple[bool, str, int]:
    """测试HTTP端点"""
    try:
        response = requests.get(url, timeout=timeout)
        return True, f"HTTP {response.status_code}", len(response.text)
    except requests.exceptions.ConnectTimeout:
        return False, "连接超时", 0
    except requests.exceptions.ReadTimeout:
        return False, "读取超时", 0
    except requests.exceptions.ConnectionError as e:
        return False, f"连接错误: {str(e)}", 0
    except Exception as e:
        return False, f"其他错误: {str(e)}", 0

def check_impala_service_status(host: str, port: int = 25000) -> Dict[str, any]:
    """检查Impala服务状态"""
    results = {
        'tcp_connection': False,
        'http_endpoints': {},
        'recommendations': []
    }
    
    print(f"检查Impala服务状态: {host}:{port}")
    print("=" * 50)
    
    # 1. TCP连接测试
    print("1. TCP连接测试...")
    tcp_ok, tcp_msg = test_tcp_connection(host, port)
    results['tcp_connection'] = tcp_ok
    print(f"   {'✓' if tcp_ok else '✗'} {tcp_msg}")
    
    if not tcp_ok:
        results['recommendations'].extend([
            "检查Impala服务是否正在运行",
            "检查防火墙设置是否阻止了端口访问",
            "验证主机名/IP地址是否正确",
            "检查网络连接是否正常"
        ])
        return results
    
    # 2. HTTP端点测试
    print("\n2. HTTP端点测试...")
    endpoints = [
        ('/', '主页'),
        ('/metrics', '指标页面'),
        ('/metrics?json', 'JSON指标'),
        ('/queries', '查询页面'),
        ('/varz', '变量页面')
    ]
    
    for endpoint, desc in endpoints:
        url = f"http://{host}:{port}{endpoint}"
        http_ok, http_msg, content_length = test_http_endpoint(url)
        results['http_endpoints'][endpoint] = {
            'success': http_ok,
            'message': http_msg,
            'content_length': content_length
        }
        
        status_icon = '✓' if http_ok else '✗'
        size_info = f" ({content_length} bytes)" if http_ok else ""
        print(f"   {status_icon} {desc}: {http_msg}{size_info}")
    
    # 3. 分析结果并给出建议
    print("\n3. 诊断结果分析...")
    
    metrics_ok = results['http_endpoints'].get('/metrics', {}).get('success', False)
    json_metrics_ok = results['http_endpoints'].get('/metrics?json', {}).get('success', False)
    
    if not metrics_ok and not json_metrics_ok:
        results['recommendations'].extend([
            "Impala Web UI可能未启用或配置错误",
            "检查Impala启动参数中的webserver相关配置",
            "确认--webserver_port参数设置正确",
            "检查Impala进程是否完全启动完成"
        ])
    elif metrics_ok and not json_metrics_ok:
        results['recommendations'].append("JSON格式指标不可用，可能是版本兼容性问题")
    elif json_metrics_ok:
        results['recommendations'].append("指标端点工作正常，可以进行监控")
    
    return results

def suggest_fixes(results: Dict[str, any]) -> None:
    """提供修复建议"""
    print("\n修复建议:")
    print("-" * 30)
    
    if not results['recommendations']:
        print("✓ 所有检查都通过，服务状态正常")
        return
    
    for i, recommendation in enumerate(results['recommendations'], 1):
        print(f"{i}. {recommendation}")
    
    print("\n常见解决方案:")
    print("-" * 30)
    print("• 重启Impala服务:")
    print("  sudo systemctl restart impala-server")
    print("  # 或")
    print("  sudo service impala-server restart")
    
    print("\n• 检查Impala配置:")
    print("  # 查看Impala进程")
    print("  ps aux | grep impalad")
    print("  # 检查端口占用")
    print("  netstat -tlnp | grep 25000")
    
    print("\n• 检查日志:")
    print("  tail -f /var/log/impala/impalad.INFO")
    print("  # 或")
    print("  journalctl -u impala-server -f")

def wait_for_service_recovery(host: str, port: int = 25000, max_wait: int = 300) -> bool:
    """等待服务恢复"""
    print(f"\n等待服务恢复 (最多等待 {max_wait} 秒)...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        tcp_ok, _ = test_tcp_connection(host, port, timeout=2)
        if tcp_ok:
            # TCP连接成功，再测试HTTP
            http_ok, _, _ = test_http_endpoint(f"http://{host}:{port}/metrics", timeout=5)
            if http_ok:
                elapsed = int(time.time() - start_time)
                print(f"✓ 服务已恢复！(等待了 {elapsed} 秒)")
                return True
        
        print(".", end="", flush=True)
        time.sleep(5)
    
    print(f"\n✗ 服务在 {max_wait} 秒内未恢复")
    return False

def main():
    parser = argparse.ArgumentParser(description='Impala连接故障诊断工具')
    parser.add_argument('host', help='Impala主机地址')
    parser.add_argument('--port', type=int, default=25000, help='Impala端口 (默认: 25000)')
    parser.add_argument('--wait', action='store_true', help='等待服务恢复')
    parser.add_argument('--max-wait', type=int, default=300, help='最大等待时间(秒)')
    
    args = parser.parse_args()
    
    # 执行诊断
    results = check_impala_service_status(args.host, args.port)
    
    # 提供修复建议
    suggest_fixes(results)
    
    # 如果指定了等待选项且服务有问题
    if args.wait and (not results['tcp_connection'] or 
                     not results['http_endpoints'].get('/metrics', {}).get('success', False)):
        if wait_for_service_recovery(args.host, args.port, args.max_wait):
            # 服务恢复后重新检查
            print("\n重新检查服务状态...")
            final_results = check_impala_service_status(args.host, args.port)
            return 0 if final_results['tcp_connection'] else 1
        else:
            return 1
    
    # 返回状态码
    return 0 if results['tcp_connection'] else 1

if __name__ == "__main__":
    sys.exit(main())
