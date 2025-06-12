#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import socket
import re
import json
import logging
from requests.exceptions import RequestException, Timeout, ConnectionError

class ePortal:
    """安徽大学校园网自动登录类"""
    
    def __init__(self, user_account, user_password, logger=None):
        """
        初始化ePortal实例
        
        Args:
            user_account: 学号
            user_password: 密码
            logger: 日志记录器，如果不提供则使用默认的
        """
        self.user_account = user_account
        self.user_password = user_password
        self.base_url = "http://172.16.253.3:801/eportal/"
        self.login_url = f"{self.base_url}?c=Portal&a=login&callback=dr1003&login_method=1&jsVersion=3.3.2&v=1117"
        self.campus_check_url = "http://172.16.253.3/a79.htm"
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "http://172.16.253.3/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 配置日志记录器
        self.logger = logger if logger else logging.getLogger(__name__)
        
        # 获取用户IP
        self.wlan_user_ip = self.get_local_ip()
        self.logger.debug(f"当前IP地址: {self.wlan_user_ip}")
    
    def get_local_ip(self):
        """
        获取本机IP地址，尝试多种方法确保获取成功
        
        Returns:
            str: 本机IP地址
        """
        ip_address = "127.0.0.1"  # 默认为本地回环地址
        
        # 方法1: 通过socket连接获取IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
            self.logger.debug(f"通过socket连接获取IP地址成功: {ip_address}")
            return ip_address
        except Exception as e:
            self.logger.warning(f"通过socket连接获取IP地址失败: {e}")
            pass
        
        # 方法2: 通过hostname获取IP
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            self.logger.debug(f"通过hostname获取IP地址成功: {ip_address}")
            return ip_address
        except Exception as e:
            self.logger.warning(f"通过hostname获取IP地址失败: {e}")
            pass
            
        # 方法3: 尝试通过网络接口列表获取IP
        try:
            import netifaces
            gws = netifaces.gateways()
            if 'default' in gws and netifaces.AF_INET in gws['default']:
                interface = gws['default'][netifaces.AF_INET][1]
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    ip_address = addrs[netifaces.AF_INET][0]['addr']
                    self.logger.debug(f"通过netifaces获取IP地址成功: {ip_address}")
                    return ip_address
        except ImportError:
            self.logger.debug("netifaces模块未安装，跳过该IP获取方法")
            pass
        except Exception as e:
            self.logger.warning(f"通过netifaces获取IP地址失败: {e}")
            pass
        
        self.logger.warning(f"所有IP获取方法均失败，使用默认IP: {ip_address}")
        return ip_address
    
    def is_connected_to_campus_network(self):
        """
        检查是否已连接到校园网（但可能尚未认证）
        
        Returns:
            bool: 是否已连接到校园网
        """
        try:
            self.logger.debug("检查是否已连接到校园网...")
            response = requests.get(self.campus_check_url, timeout=5, headers=self.headers)
            is_connected = response.status_code == 200
            self.logger.debug(f"校园网连接状态: {'已连接' if is_connected else '未连接'}")
            return is_connected
        except ConnectionError:
            self.logger.warning("网络连接错误，无法连接到校园网认证页面")
            return False
        except Timeout:
            self.logger.warning("连接校园网认证页面超时")
            return False
        except Exception as e:
            self.logger.warning(f"检查校园网连接时发生异常: {e}")
            return False
    
    def login(self):
        """
        执行登录操作，包含完整的异常处理和重试机制
        
        Returns:
            bool: 登录是否成功
            str: 登录结果信息
        """
        # 首先检查是否已连接到校园网
        if not self.is_connected_to_campus_network():
            self.logger.warning("尚未连接校园网，登录失败")
            return False, "尚未连接校园网"
            
        try:
            # 构建登录参数
            params = {
                "c": "Portal",
                "a": "login",
                "callback": "dr1003",
                "login_method": "1",
                "user_account": self.user_account,
                "user_password": self.user_password,
                "wlan_user_ip": self.wlan_user_ip,
                "wlan_user_ipv6": "",
                "wlan_user_mac": "000000000000",
                "wlan_ac_ip": "",
                "wlan_ac_name": "",
                "jsVersion": "3.3.2",
                "v": "1117"
            }
            
            self.logger.debug("开始发送登录请求...")
            
            # 发送登录请求（添加重试机制）
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    response = requests.get(
                        self.login_url, 
                        params=params,
                        headers=self.headers,
                        timeout=10
                    )
                    break
                except Timeout:
                    retry_count += 1
                    if retry_count < max_retries:
                        self.logger.warning(f"登录请求超时，正在进行第{retry_count}次重试...")
                    else:
                        self.logger.error("登录请求超时，已达到最大重试次数")
                        return False, "登录请求超时，请检查网络连接"
                except ConnectionError:
                    self.logger.error("网络连接错误，无法连接到校园网认证服务器")
                    return False, "无法连接到校园网认证服务器，请检查网络连接"
                except Exception as e:
                    self.logger.error(f"发送登录请求时发生未知异常: {e}")
                    return False, f"登录过程中发生异常: {str(e)}"
            
            # 处理返回结果
            if response.status_code == 200:
                self.logger.debug("登录请求已发送，正在解析返回结果...")
                
                # 提取JSON数据 (通常在dr1003()中)
                json_str = re.search(r'dr1003\((.*)\)', response.text)
                if json_str:
                    result = json.loads(json_str.group(1))
                    if result.get("result") == "1":
                        self.logger.info(f"用户 {self.user_account} 登录成功")
                        return True, "登录成功"
                    else:
                        error_msg = result.get("msg", "登录失败，未知原因")
                        self.logger.warning(f"登录失败: {error_msg}")
                        return False, error_msg
                else:
                    self.logger.error("登录失败，无法解析返回数据")
                    self.logger.debug(f"服务器返回内容: {response.text[:200]}...")
                    return False, "登录失败，无法解析返回数据"
            else:
                self.logger.error(f"登录失败，HTTP状态码: {response.status_code}")
                return False, f"登录失败，HTTP状态码: {response.status_code}"
        
        except Exception as e:
            self.logger.error(f"登录过程中发生异常: {e}")
            return False, f"登录过程中发生异常: {str(e)}"
    
    def check_login_status(self):
        """
        检查当前登录状态
        
        Returns:
            bool: 是否已登录
        """
        try:
            # 尝试访问外部网站检查是否已登录
            test_url = "http://www.baidu.com"
            response = requests.get(test_url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False


# 使用示例
if __name__ == "__main__":
    import getpass
    
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("ePortal")
    
    user_account = input("请输入学号: ")
    user_password = getpass.getpass("请输入密码: ")
    
    portal = ePortal(user_account, user_password, logger=logger)
    success, message = portal.login()
    print(message) 