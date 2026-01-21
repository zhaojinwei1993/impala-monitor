#!/usr/bin/env python3
"""
Impala Query Killer
监控并自动 kill 超时或超内存的查询
"""

import os
import time
import logging
import argparse
import requests
from datetime import datetime
from typing import List, Dict, Any
from impala_exporter import ImpalaExporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_file: str) -> Dict[str, str]:
    """加载配置文件"""
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config


class QueryKiller:
    def __init__(self, impala_host: str, impala_port: int = 25000, 
                 feishu_webhook: str = None, check_interval: int = 60):
        self.impala_host = impala_host
        self.impala_port = impala_port
        self.feishu_webhook = feishu_webhook
        self.check_interval = check_interval
        self.exporter = ImpalaExporter(impala_host, impala_port)
        
        # 阈值配置
        self.max_duration_seconds = 600  # 10分钟
        self.max_memory_bytes = 1024 ** 4  # 1TB
    
    def _parse_memory_string(self, mem_str: str) -> float:
        """解析内存字符串为字节数"""
        if not mem_str or mem_str == '0':
            return 0
        
        mem_str = mem_str.strip().upper()
        multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        
        for unit, multiplier in multipliers.items():
            if mem_str.endswith(unit):
                try:
                    return float(mem_str[:-len(unit)].strip()) * multiplier
                except ValueError:
                    continue
        
        try:
            return float(mem_str)
        except ValueError:
            return 0
    
    def _parse_duration_string(self, duration_str: str) -> float:
        """解析时间字符串为秒数"""
        if not duration_str:
            return 0
        
        import re
        
        # 处理毫秒
        ms_match = re.match(r'(\d+(?:\.\d+)?)ms', duration_str.strip())
        if ms_match:
            return float(ms_match.group(1)) / 1000.0
        
        # 处理标准格式
        match = re.match(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?', duration_str.strip())
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = float(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        
        return 0
    
    def _kill_query(self, query_id: str) -> bool:
        """Kill 指定查询"""
        try:
            url = f"http://{self.impala_host}:{self.impala_port}/cancel_query?query_id={query_id}"
            logger.info(f"Sending cancel request to: {url}")
            # cancel 操作可能需要较长时间，增加超时到 60 秒
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                logger.info(f"Successfully killed query: {query_id}")
                return True
            else:
                logger.error(f"Failed to kill query {query_id}: {response.status_code}, response: {response.text}")
                return False
        except Exception as e:
            # 检查是否是超时错误（包括 ReadTimeout）
            error_msg = str(e)
            if 'timed out' in error_msg.lower() or 'timeout' in error_msg.lower():
                # 超时时，等待几秒后验证查询是否还存在
                logger.warning(f"Cancel request timeout for query {query_id}: {e}")
                logger.info(f"Waiting 5 seconds to verify if query was killed...")
                time.sleep(5)
                
                # 检查查询是否还在运行
                if self._is_query_running(query_id):
                    logger.error(f"Query {query_id} is still running after cancel timeout")
                    return False
                else:
                    logger.info(f"Query {query_id} is no longer running, cancel was successful")
                    return True
            else:
                logger.error(f"Error killing query {query_id}: {e}")
                return False
    
    def _is_query_running(self, query_id: str) -> bool:
        """检查查询是否还在运行"""
        try:
            all_metrics = self.exporter.get_all_metrics()
            queries = all_metrics.get('query_details', [])
            for query in queries:
                if query.get('query_id') == query_id and query.get('state') == 'RUNNING':
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking query status: {e}")
            # 出错时保守处理，假设查询还在运行
            return True
    
    def _send_feishu_notification(self, query: Dict[str, Any], reason: str):
        """发送飞书通知"""
        if not self.feishu_webhook:
            logger.warning("Feishu webhook not configured, skipping notification")
            return
        
        mem_usage = self._parse_memory_string(query.get('mem_usage', '0'))
        mem_gb = mem_usage / (1024**3)
        duration = self._parse_duration_string(query.get('duration', '0'))
        duration_min = duration / 60
        
        message = (
            f"⚠️ query-killer: Impala 查询已被自动终止\n\n"
            f"节点：{self.impala_host}\n"
            f"查询用户：{query.get('effective_user', 'unknown')}\n"
            f"查询 query_id：{query.get('query_id', 'unknown')}\n"
            f"查询时间：{query.get('start_time', 'unknown')}\n"
            f"运行时长：{duration_min:.1f} 分钟\n"
            f"查询内存：{mem_gb:.2f} GB\n"
            f"终止原因：{reason}\n\n"
            f"该 SQL 运行时间/占用内存过大影响到集群稳定性，请优化 SQL 或者使用 hive on spark 进行查询。"
        )
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        
        try:
            logger.info(f"Sending Feishu notification for query {query.get('query_id')}")
            response = requests.post(self.feishu_webhook, json=payload, timeout=10)
            logger.info(f"Feishu response status: {response.status_code}, body: {response.text}")
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    logger.info(f"Feishu notification sent successfully for query {query.get('query_id')}")
                else:
                    logger.error(f"Feishu API error: {result}")
            else:
                logger.error(f"Failed to send Feishu notification: {response.status_code}, {response.text}")
        except Exception as e:
            logger.error(f"Error sending Feishu notification: {e}", exc_info=True)
    
    def check_and_kill_queries(self):
        """检查并 kill 超标查询"""
        try:
            all_metrics = self.exporter.get_all_metrics()
            queries = all_metrics.get('query_details', [])
            
            for query in queries:
                # 跳过非运行状态
                if query.get('state') != 'RUNNING':
                    continue
                
                # 跳过 GET_SCHEMAS
                if query.get('stmt') == 'GET_SCHEMAS':
                    continue

                # 跳过 root 用户的查询
                if query.get('effective_user') == 'root':
                    continue

                
                query_id = query.get('query_id', '')
                mem_usage = self._parse_memory_string(query.get('mem_usage', '0'))
                duration = self._parse_duration_string(query.get('duration', '0'))
                
                # 检查是否超标
                should_kill = False
                reason = ""
                
                if duration > self.max_duration_seconds:
                    should_kill = True
                    reason = f"运行时间超过 {self.max_duration_seconds/60:.0f} 分钟"
                    logger.warning(f"Query {query_id} exceeded time limit: {duration:.0f}s")
                
                if mem_usage > self.max_memory_bytes:
                    should_kill = True
                    mem_tb = mem_usage / (1024**4)
                    reason = f"内存使用超过 {self.max_memory_bytes/(1024**4):.0f} TB (当前: {mem_tb:.2f} TB)"
                    logger.warning(f"Query {query_id} exceeded memory limit: {mem_usage/(1024**3):.2f}GB")
                
                if should_kill:
                    logger.info(f"Killing query {query_id}: {reason}")
                    if self._kill_query(query_id):
                        self._send_feishu_notification(query, reason)
                    
        except Exception as e:
            logger.error(f"Error in check_and_kill_queries: {e}")
    
    def run(self):
        """运行监控循环"""
        logger.info(f"Starting Query Killer for {self.impala_host}:{self.impala_port}")
        logger.info(f"Max duration: {self.max_duration_seconds}s, Max memory: {self.max_memory_bytes/(1024**4):.1f}TB")
        
        while True:
            try:
                self.check_and_kill_queries()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(self.check_interval)


def main():
    parser = argparse.ArgumentParser(description='Impala Query Killer')
    parser.add_argument('--config', default='/opt/impala-monitor/config/query_killer.conf', 
                        help='Config file path')
    parser.add_argument('--host', help='Impala host (overrides config)')
    parser.add_argument('--port', type=int, help='Impala port (overrides config)')
    parser.add_argument('--feishu-webhook', help='Feishu webhook URL (overrides config)')
    parser.add_argument('--check-interval', type=int, help='Check interval in seconds (overrides config)')
    parser.add_argument('--max-duration', type=int, help='Max duration in seconds (overrides config)')
    parser.add_argument('--max-memory-gb', type=int, help='Max memory in GB (overrides config)')
    
    args = parser.parse_args()
    
    # 加载配置文件
    config = load_config(args.config)
    
    # 命令行参数优先，否则使用配置文件
    impala_host = args.host or config.get('IMPALA_HOST')
    impala_port = args.port or int(config.get('IMPALA_PORT', 25000))
    feishu_webhook = args.feishu_webhook or config.get('FEISHU_WEBHOOK')
    check_interval = args.check_interval or int(config.get('CHECK_INTERVAL', 60))
    max_duration = args.max_duration or int(config.get('MAX_DURATION', 600))
    max_memory_gb = args.max_memory_gb or int(config.get('MAX_MEMORY_GB', 1024))
    
    if not impala_host:
        logger.error("IMPALA_HOST is required in config file or --host argument")
        return
    
    killer = QueryKiller(
        impala_host=impala_host,
        impala_port=impala_port,
        feishu_webhook=feishu_webhook,
        check_interval=check_interval
    )
    
    # 设置阈值
    killer.max_duration_seconds = max_duration
    killer.max_memory_bytes = max_memory_gb * (1024**3)
    
    killer.run()


if __name__ == '__main__':
    main()
