#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import os
import logging
from requests.exceptions import RequestException, Timeout, ConnectionError
import socket
import platform

class Notifier:
    """通知模块，用于发送消息通知"""
    
    def __init__(self, webhook_urls, logger=None):
        """
        初始化通知器实例
        
        Args:
            webhook_urls: webhook URL的列表或字符串
            logger: 日志记录器，如果不提供则使用默认的
        """
        # 配置日志记录器
        self.logger = logger if logger else logging.getLogger(__name__)
        
        if isinstance(webhook_urls, str):
            self.webhook_urls = [webhook_urls]
        elif isinstance(webhook_urls, list):
            self.webhook_urls = webhook_urls
        else:
            self.webhook_urls = []
            self.logger.warning("无效的webhook URLs格式，应为字符串或列表")
        
        # 获取系统代理设置
        self.proxies = self._get_system_proxies()
        
        # 检查webhook URL是否有效
        self._validate_webhook_urls()
    
    def _validate_webhook_urls(self):
        """验证webhook URL的有效性"""
        valid_urls = []
        for url in self.webhook_urls:
            if not url:
                continue
                
            if not url.startswith("http"):
                self.logger.warning(f"无效的webhook URL格式: {url}")
                continue
                
            valid_urls.append(url)
            
        if not valid_urls and self.webhook_urls:
            self.logger.warning("所有webhook URL均无效")
            
        self.webhook_urls = valid_urls
    
    def _get_system_proxies(self):
        """
        获取系统代理设置
        
        Returns:
            dict: 包含http和https代理的字典，如果没有代理则返回空字典
        """
        proxies = {}
        # 检查环境变量中的代理设置
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        no_proxy = os.environ.get('NO_PROXY') or os.environ.get('no_proxy')
        
        if http_proxy:
            proxies['http'] = http_proxy
            self.logger.debug(f"检测到HTTP代理: {http_proxy}")
            
        if https_proxy:
            proxies['https'] = https_proxy
            self.logger.debug(f"检测到HTTPS代理: {https_proxy}")
            
        if no_proxy:
            self.logger.debug(f"检测到NO_PROXY设置: {no_proxy}")
            
        # 如果没有在环境变量中找到代理，则尝试使用requests的系统代理检测
        if not proxies:
            try:
                system_proxies = requests.utils.get_environ_proxies('')
                if system_proxies:
                    proxies = system_proxies
                    self.logger.debug(f"从系统检测到代理设置: {system_proxies}")
            except Exception as e:
                self.logger.warning(f"获取系统代理时发生错误: {str(e)}")
                
        # 检查Linux系统特定的代理配置
        if platform.system() == 'Linux' and not proxies:
            try:
                # 检查/etc/environment文件
                if os.path.exists('/etc/environment'):
                    with open('/etc/environment', 'r') as f:
                        for line in f:
                            if 'http_proxy' in line.lower():
                                parts = line.strip().split('=', 1)
                                if len(parts) == 2:
                                    proxies['http'] = parts[1].strip('"\'')
                                    self.logger.debug(f"从/etc/environment检测到HTTP代理: {proxies['http']}")
                            elif 'https_proxy' in line.lower():
                                parts = line.strip().split('=', 1)
                                if len(parts) == 2:
                                    proxies['https'] = parts[1].strip('"\'')
                                    self.logger.debug(f"从/etc/environment检测到HTTPS代理: {proxies['https']}")
            except Exception as e:
                self.logger.warning(f"读取Linux代理配置时发生错误: {str(e)}")
                
        return proxies
    
    def send_text(self, content, mentioned_list=None, mentioned_mobile_list=None):
        """
        发送文本消息
        
        Args:
            content: 消息内容
            mentioned_list: 要@的成员ID列表
            mentioned_mobile_list: 要@的成员手机号列表
            
        Returns:
            bool: 是否发送成功
        """
        if not self.webhook_urls:
            self.logger.warning("没有有效的webhook URL，无法发送通知")
            return False
            
        # 增加系统信息
        system_info = f"\n系统信息: {platform.system()} {platform.release()}"
        hostname = socket.gethostname()
        system_info += f"\n主机名: {hostname}"
        
        full_content = f"{content}{system_info}"
        
        data = {
            "msgtype": "text",
            "text": {
                "content": full_content,
                "mentioned_list": mentioned_list or [],
                "mentioned_mobile_list": mentioned_mobile_list or [],
            },
        }
        return self._send(data)
    
    def send_markdown(self, content):
        """
        发送markdown格式的消息
        
        Args:
            content: markdown格式的消息内容
            
        Returns:
            bool: 是否发送成功
        """
        if not self.webhook_urls:
            self.logger.warning("没有有效的webhook URL，无法发送通知")
            return False
            
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        return self._send(data)
    
    def _send(self, data, webhook_url=None):
        """
        发送消息到指定的webhook URL，包含完整的错误处理和重试逻辑
        
        Args:
            data: 要发送的消息数据
            webhook_url: 要发送的webhook URL，如果不指定，则发送到所有webhook URLs
            
        Returns:
            bool: 是否发送成功
        """
        if webhook_url is None:
            webhooks = self.webhook_urls
        else:
            webhooks = [webhook_url]

        if not webhooks:
            self.logger.warning("没有有效的webhook URL，无法发送通知")
            return False

        success = False
        for webhook in webhooks:
            try:
                self.logger.debug(f"正在向webhook发送通知: {webhook}")
                headers = {"Content-Type": "application/json"}
                
                # 添加重试机制
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        # 使用系统代理发送请求
                        response = requests.post(
                            webhook, 
                            headers=headers, 
                            data=json.dumps(data),
                            proxies=self.proxies if self.proxies else None,  # 如果有代理则使用
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            resp_json = response.json()
                            if resp_json.get("errcode") == 0:
                                self.logger.debug("通知发送成功")
                                success = True
                                break
                            else:
                                self.logger.warning(f"发送消息失败: {resp_json}")
                        else:
                            self.logger.warning(f"发送消息失败，HTTP状态码: {response.status_code}")
                            
                        retry_count += 1
                        if retry_count < max_retries:
                            self.logger.debug(f"正在尝试第{retry_count+1}次重试...")
                            
                    except Timeout:
                        retry_count += 1
                        if retry_count < max_retries:
                            self.logger.warning(f"请求超时，正在进行第{retry_count}次重试...")
                        else:
                            self.logger.error("请求超时，已达到最大重试次数")
                    except ConnectionError:
                        self.logger.error(f"连接错误，无法连接到webhook: {webhook}")
                        break
                    except Exception as e:
                        self.logger.error(f"发送消息过程中发生未知异常: {str(e)}")
                        break
                        
            except Exception as e:
                self.logger.error(f"发送消息到{webhook}时发生异常: {str(e)}")
                
        return success


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("Notifier")
    
    # 初始化通知器
    webhook_url = input("请输入企业微信webhook URL: ")
    notifier = Notifier(webhook_urls=webhook_url, logger=logger)
    
    # 发送即时消息
    success = notifier.send_text("这是一条来自Linux的测试消息")
    print(f"消息发送{'成功' if success else '失败'}")
    
    # 打印当前使用的代理
    print(f"当前系统代理设置: {notifier.proxies}") 