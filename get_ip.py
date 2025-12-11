#!/usr/bin/env python3
"""
获取本机 IP 地址的测试脚本
"""

import socket
import subprocess

def get_eth0_ip():
    """获取 eth0 网卡的 IP 地址"""
    print("尝试获取 eth0 网卡 IP 地址...")
    
    try:
        # 方法1: 使用 ip 命令
        print("方法1: 使用 ip addr show eth0")
        result = subprocess.run(['ip', 'addr', 'show', 'eth0'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("命令输出:")
            print(result.stdout)
            for line in result.stdout.split('\n'):
                if 'inet ' in line and not '127.0.0.1' in line:
                    ip = line.strip().split()[1].split('/')[0]
                    print(f"从 eth0 获取到 IP: {ip}")
                    return ip
        else:
            print(f"命令执行失败: {result.stderr}")
    except Exception as e:
        print(f"方法1 失败: {e}")
    
    try:
        # 方法2: 使用 socket 连接外部地址获取本地 IP
        print("\n方法2: 使用 socket 连接外部地址")
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(f"通过 socket 获取到 IP: {ip}")
        return ip
    except Exception as e:
        print(f"方法2 失败: {e}")
    
    try:
        # 方法3: 使用 hostname -I
        print("\n方法3: 使用 hostname -I")
        result = subprocess.run(['hostname', '-I'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            ip = result.stdout.strip().split()[0]
            print(f"通过 hostname -I 获取到 IP: {ip}")
            return ip
        else:
            print(f"命令执行失败: {result.stderr}")
    except Exception as e:
        print(f"方法3 失败: {e}")
    
    print("\n所有方法都失败，返回 localhost")
    return 'localhost'

if __name__ == '__main__':
    ip = get_eth0_ip()
    print(f"\n最终获取的 IP 地址: {ip}")
    
    # 测试连接
    print(f"\n测试连接 Impala: http://{ip}:25000/metrics?json")
    try:
        import requests
        response = requests.get(f"http://{ip}:25000/metrics?json", timeout=5)
        print(f"连接成功，状态码: {response.status_code}")
    except Exception as e:
        print(f"连接失败: {e}")
