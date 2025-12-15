# Impala Monitor 卸载指南

## 概述

本文档描述如何从多个节点完全卸载 Impala Monitor 监控采集程序。

## 卸载内容

卸载过程将移除以下组件：

### 服务和进程
- `impala-monitor.service` (原版本)
- `impala-monitor-v2.service` (V2版本)
- 所有相关的 systemd 服务文件

### 文件和目录
- `/opt/impala-monitor/` (完整安装目录)
- `/etc/systemd/system/impala-monitor*.service` (服务文件)
- `/var/log/impala-monitor*.log` (日志文件)
- `/tmp/*impala-monitor*` (临时文件)

### 系统配置
- `impala-monitor` 系统用户
- 防火墙规则 (端口 9356, 9357)
- Python 包 (可选)

### 备份
- 配置文件会备份到 `/tmp/impala-monitor-config-backup-<timestamp>/`

## 准备工作

### 1. 检查当前部署

首先查看当前的部署状态：

```bash
# 查看当前清单
cd /Users/zhaojinwei/impala-monitor/ansible/scripts
./uninstall.sh --show-inventory
```

### 2. 配置清单文件

编辑 `ansible/inventory/inventory.ini` 文件，确保包含所有需要卸载的节点：

```ini
[impala_nodes]
impala-node1 ansible_host=192.168.1.101 ansible_user=root
impala-node2 ansible_host=192.168.1.102 ansible_user=root
impala-node3 ansible_host=192.168.1.103 ansible_user=root

[impala_nodes:vars]
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
ansible_python_interpreter=/usr/bin/python3
ansible_become=yes
```

### 3. 测试连接

验证 Ansible 可以连接到所有节点：

```bash
cd /Users/zhaojinwei/impala-monitor/ansible
ansible -i inventory/inventory.ini impala_nodes -m ping
```

## 卸载方法

### 方法一：完全卸载（推荐）

完全卸载所有组件：

```bash
cd /Users/zhaojinwei/impala-monitor/ansible/scripts
./uninstall.sh
```

### 方法二：保留 Python 包

如果其他应用也使用相同的 Python 包，可以不删除它们：

```bash
./uninstall.sh
# 不使用 --remove-packages 选项
```

### 方法三：部分节点卸载

只从特定节点卸载：

```bash
./uninstall.sh --limit node1,node2
```

### 方法四：干运行模式

先检查会删除什么，不实际执行：

```bash
./uninstall.sh --dry-run
```

## 卸载选项

### 命令行选项

```bash
./uninstall.sh [OPTIONS]

选项:
  --remove-packages    同时删除 Python 包
  --limit HOSTS        限制到特定主机
  --dry-run           检查模式（不实际更改）
  --verify            仅验证是否已卸载
  --show-inventory    显示当前清单配置
  --help              显示帮助信息
```

### 使用示例

```bash
# 完全卸载所有节点
./uninstall.sh

# 只卸载特定节点
./uninstall.sh --limit impala-node1,impala-node2

# 包括删除 Python 包
./uninstall.sh --remove-packages

# 检查模式（不实际删除）
./uninstall.sh --dry-run

# 验证是否已完全卸载
./uninstall.sh --verify
```

## 卸载流程

### 1. 执行卸载

```bash
cd /Users/zhaojinwei/impala-monitor/ansible/scripts
./uninstall.sh
```

卸载过程会显示：
- 目标主机列表
- 确认提示
- 执行进度
- 验证结果

### 2. 确认卸载

脚本会要求确认：

```
This will COMPLETELY REMOVE Impala Monitor from all nodes in the inventory!
The following will be removed:
  - Impala Monitor services (both original and V2)
  - Installation directory (/opt/impala-monitor)
  - System user (impala-monitor)
  - Firewall rules
  - Service files

Configuration will be backed up to /tmp/ before removal.

Are you sure you want to continue? (yes/no):
```

输入 `yes` 继续。

### 3. 监控进度

卸载过程中会显示每个步骤的执行状态：

```
TASK [Stop V2 service if running] *************************************
ok: [impala-node1]
ok: [impala-node2]

TASK [Remove installation directory] **********************************
changed: [impala-node1]
changed: [impala-node2]
```

### 4. 验证结果

卸载完成后，脚本会询问是否验证：

```
Do you want to verify the uninstallation? (y/n):
```

选择 `y` 进行验证。

## 验证卸载

### 自动验证

使用内置验证功能：

```bash
./uninstall.sh --verify
```

### 手动验证

在每个节点上检查：

```bash
# 检查服务
systemctl list-unit-files | grep impala-monitor

# 检查目录
ls -la /opt/impala-monitor

# 检查用户
id impala-monitor

# 检查进程
ps aux | grep impala

# 检查端口
netstat -tlnp | grep 9356
```

所有检查都应该返回空结果或错误。

## 故障排除

### 1. 连接失败

如果 Ansible 无法连接到节点：

```bash
# 检查 SSH 连接
ssh user@node_ip

# 检查 SSH 密钥
ssh-add -l

# 测试 Ansible 连接
ansible -i inventory/inventory.ini node_name -m ping -vvv
```

### 2. 权限问题

如果遇到权限错误：

```bash
# 确保使用 sudo
ansible-playbook ... --become --ask-become-pass

# 或在清单中配置
ansible_become=yes
ansible_become_method=sudo
```

### 3. 服务无法停止

如果服务无法停止：

```bash
# 手动强制停止
sudo systemctl kill impala-monitor
sudo systemctl kill impala-monitor-v2

# 检查进程
sudo pkill -f impala-monitor
```

### 4. 目录无法删除

如果目录删除失败：

```bash
# 检查文件占用
sudo lsof +D /opt/impala-monitor

# 强制删除
sudo rm -rf /opt/impala-monitor
```

### 5. 用户无法删除

如果用户删除失败：

```bash
# 检查用户进程
sudo pkill -u impala-monitor

# 强制删除用户
sudo userdel -r impala-monitor
```

## 恢复配置

如果需要恢复配置：

```bash
# 查找备份
ls -la /tmp/impala-monitor-config-backup-*

# 恢复配置
sudo cp -r /tmp/impala-monitor-config-backup-*/config /opt/impala-monitor/
```

## 重新安装

如果需要重新安装：

```bash
# 使用原部署脚本
cd /Users/zhaojinwei/impala-monitor/ansible/scripts
./deploy.sh

# 或使用 V2 版本
cd /Users/zhaojinwei/impala-monitor/monitor/scripts
sudo ./deploy_node_collector_v2.sh install
```

## 清理 Prometheus 配置

卸载后，记得更新 Prometheus 配置：

```yaml
# 从 prometheus.yml 中移除
scrape_configs:
  - job_name: 'impala-nodes'
    static_configs:
      - targets: ['node1:9356', 'node2:9356']  # 删除这些
```

重启 Prometheus：

```bash
sudo systemctl restart prometheus
```

## 清理 Grafana 仪表板

在 Grafana 中：

1. 删除 Impala 相关的仪表板
2. 删除相关的告警规则
3. 清理数据源（如果不再需要）

## 注意事项

1. **备份重要数据**：卸载前确保备份重要的配置和数据
2. **停止依赖服务**：确保没有其他服务依赖 Impala Monitor
3. **通知团队**：卸载前通知相关团队成员
4. **更新文档**：更新相关的运维文档和监控配置
5. **验证完整性**：卸载后验证所有组件都已正确移除

## 支持

如果遇到问题：

1. 查看 Ansible 详细输出：`-vvv`
2. 检查目标节点的系统日志
3. 使用 `--dry-run` 模式预览操作
4. 逐个节点进行卸载：`--limit node_name`
