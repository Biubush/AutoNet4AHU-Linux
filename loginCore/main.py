#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import argparse
import logging
import sys
import time
import datetime
import socket
import platform
import traceback
from pathlib import Path
import signal

try:
    import systemd.journal
    has_systemd = True
except ImportError:
    has_systemd = False

from portal import ePortal
from notify import Notifier
from version import VERSION, get_version_info

class AutoLogin:
    """校园网自动登录入口模块"""
    
    def __init__(self, config_file="config.json"):
        """
        初始化自动登录实例
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self.load_config()
        self.setup_logger()
        
        # 注册信号处理程序
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        
        self.logger.info(f"AutoNet4AHU v{VERSION} 启动，配置文件: {config_file}")
        self.logger.debug(f"当前系统: {platform.system()} {platform.release()}")
        self.logger.debug(f"主机名: {socket.gethostname()}")
        
    def handle_signal(self, signum, frame):
        """处理终止信号"""
        self.logger.info(f"收到信号 {signum}，准备退出")
        sys.exit(0)
    
    def setup_logger(self):
        """设置日志记录器"""
        # 获取日志级别
        log_level_name = self.config.get("log_level", "INFO").upper()
        log_level = getattr(logging, log_level_name, logging.INFO)
        
        # 创建日志记录器
        self.logger = logging.getLogger("AutoNet4AHU")
        self.logger.setLevel(log_level)
        
        # 清除可能已存在的处理器
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # 将处理器添加到日志记录器
        self.logger.addHandler(console_handler)
        
        # 如果支持systemd，添加systemd journal处理器
        if has_systemd:
            try:
                journal_handler = systemd.journal.JournalHandler(
                    SYSLOG_IDENTIFIER="autonet4ahu"
                )
                journal_handler.setLevel(log_level)
                self.logger.addHandler(journal_handler)
                self.logger.debug("已添加systemd journal日志处理器")
            except Exception as e:
                self.logger.warning(f"添加systemd journal处理器失败: {e}")
        
        # 如果系统目录可写，添加文件处理器
        log_dirs = [
            "/var/log/autonet4ahu",
            os.path.expanduser("~/.local/share/autonet4ahu/logs"),
            os.path.dirname(os.path.abspath(self.config_file))
        ]
        
        log_file = None
        for log_dir in log_dirs:
            try:
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, "autonet4ahu.log")
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(log_level)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                self.logger.debug(f"日志将保存到: {log_file}")
                break
            except (PermissionError, OSError):
                continue
        
        if not log_file:
            self.logger.warning("无法创建日志文件，将只输出到控制台和systemd journal")
    
    def load_config(self):
        """
        加载配置文件，如果不存在则尝试在多个位置查找
        
        Returns:
            dict: 配置信息
        """
        default_config = {
            "student_id": "",
            "password": "",
            "webhook_urls": [],
            "log_level": "INFO"
        }
        
        # 如果直接指定的配置文件存在，则使用它
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                return config
            except Exception as e:
                print(f"加载配置文件 {self.config_file} 失败: {e}")
                pass
        
        # 尝试在其他常见位置查找配置文件
        config_paths = [
            "/etc/autonet4ahu/config.json",  # 系统级配置
            os.path.expanduser("~/.config/autonet4ahu/config.json"),  # 用户级配置
            "config.json"  # 当前目录
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    self.config_file = config_path  # 更新配置文件路径
                    print(f"已加载配置: {config_path}")
                    return config
                except Exception as e:
                    print(f"加载配置文件 {config_path} 失败: {e}")
                    pass
        
        print("警告: 未找到有效配置，使用默认配置")
        return default_config
    
    def config_is_complete(self):
        """
        检查配置是否完整
        
        Returns:
            bool: 配置是否包含必要的信息
        """
        return bool(self.config.get("student_id")) and bool(self.config.get("password"))
    
    def login(self, retry_count=1, retry_interval=30):
        """
        执行登录操作，如果配置不完整则直接退出
        
        Args:
            retry_count: 登录失败时的重试次数
            retry_interval: 重试间隔（秒）
            
        Returns:
            bool: 登录是否成功
        """
        # 检查配置是否完整，不完整则直接退出
        if not self.config_is_complete():
            self.logger.error(f"配置不完整，请配置{self.config_file}文件设置学号和密码")
            return False
        
        student_id = self.config.get("student_id")
        password = self.config.get("password")
        
        # 使用ePortal进行登录
        try:
            portal = ePortal(student_id, password, logger=self.logger)
            
            # 检查当前是否已成功登录
            if portal.check_login_status():
                self.logger.info("已经成功登录校园网，无需再次登录")
                return True
                
            self.logger.info("开始登录校园网...")
            success, message = portal.login()
            
            # 如果登录失败且有重试次数，则进行重试
            attempts = 1
            while not success and attempts < retry_count:
                self.logger.warning(f"登录失败，{retry_interval}秒后进行第{attempts+1}/{retry_count}次重试")
                time.sleep(retry_interval)
                attempts += 1
                success, message = portal.login()
            
            # 发送通知（如果配置了webhook URLs）
            webhook_urls = self.config.get("webhook_urls")
            if webhook_urls:
                self.send_notification(success, message, portal.wlan_user_ip)
            
            if success:
                self.logger.info(f"登录成功: {message}")
            else:
                self.logger.error(f"登录失败: {message}")
                
            return success
        except Exception as e:
            self.logger.error(f"登录过程中发生未处理的异常: {e}")
            self.logger.error(traceback.format_exc())
            
            # 尝试发送错误通知
            try:
                webhook_urls = self.config.get("webhook_urls")
                if webhook_urls:
                    notifier = Notifier(webhook_urls, logger=self.logger)
                    error_content = f"校园网登录异常通知\n\n" \
                                    f"学号: {self.config.get('student_id')}\n" \
                                    f"错误信息: {str(e)}\n" \
                                    f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    notifier.send_text(error_content)
            except Exception:
                self.logger.error("发送错误通知失败")
            
            return False
    
    def send_notification(self, success, message, ip_address):
        """
        发送登录结果通知
        
        Args:
            success: 是否登录成功
            message: 登录结果消息
            ip_address: 当前IP地址
        """
        webhook_urls = self.config.get("webhook_urls", [])
        if not webhook_urls:
            self.logger.debug("未配置webhook URLs，跳过通知")
            return
        
        self.logger.debug("发送登录结果通知...")
        try:
            notifier = Notifier(webhook_urls, logger=self.logger)
            
            status = "成功" if success else "失败"
            content = f"校园网登录{status}通知\n\n" \
                     f"学号: {self.config.get('student_id')}\n" \
                     f"IP地址: {ip_address}\n" \
                     f"登录结果: {message}\n" \
                     f"程序版本: v{VERSION}\n" \
                     f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            if notifier.send_text(content):
                self.logger.debug("通知发送成功")
            else:
                self.logger.warning("通知发送失败")
        except Exception as e:
            self.logger.error(f"发送通知过程中发生异常: {e}")
    
    def daemon_mode(self, check_interval=300):
        """
        守护进程模式，定期检查并保持登录状态
        
        Args:
            check_interval: 检查间隔（秒）
        """
        self.logger.info(f"进入守护进程模式，检查间隔: {check_interval}秒")
        
        try:
            while True:
                # 执行登录操作
                try:
                    self.login(retry_count=3, retry_interval=10)
                except Exception as e:
                    self.logger.error(f"登录过程中发生异常: {e}")
                    self.logger.error(traceback.format_exc())
                
                # 等待指定时间
                self.logger.debug(f"休眠{check_interval}秒后再次检查")
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            self.logger.info("接收到终止信号，程序退出")
        except Exception as e:
            self.logger.critical(f"守护进程模式发生严重异常: {e}")
            self.logger.critical(traceback.format_exc())
            sys.exit(1)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="安徽大学校园网自动登录工具")
    parser.add_argument("-c", "--config", help="指定配置文件路径", default="config.json")
    parser.add_argument("-d", "--daemon", action="store_true", help="以守护进程模式运行，定期检查登录状态")
    parser.add_argument("-i", "--interval", type=int, default=300, help="守护进程模式下的检查间隔（秒），默认300秒")
    parser.add_argument("-r", "--retry", type=int, default=3, help="登录失败时的重试次数，默认3次")
    parser.add_argument("-v", "--version", action="store_true", help="显示版本信息")
    parser.add_argument("command", nargs="?", default="login", help="执行的命令，目前支持: login, daemon")
    
    return parser.parse_args()


def main():
    """程序入口点"""
    try:
        args = parse_args()
        
        # 显示版本信息
        if args.version:
            print(get_version_info())
            return
        
        # 使用指定的配置文件路径创建AutoLogin实例
        auto_login = AutoLogin(config_file=args.config)
        
        # 根据命令或参数执行对应操作
        if args.daemon or args.command == "daemon":
            auto_login.daemon_mode(check_interval=args.interval)
        elif args.command == "login":
            success = auto_login.login(retry_count=args.retry)
            sys.exit(0 if success else 1)
        else:
            auto_login.logger.error(f"未知命令: {args.command}")
            auto_login.logger.info("可用命令: login, daemon")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序发生致命错误: {e}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main() 