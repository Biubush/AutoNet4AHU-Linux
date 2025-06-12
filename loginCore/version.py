#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""版本信息模块"""

import os
import sys
import platform
import datetime

# 版本号（发布时自动更新）
VERSION = "1.0.0"
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
BUILD_SYSTEM = f"{platform.system()} {platform.release()}"
PYTHON_VERSION = platform.python_version()

def get_version_info():
    """获取格式化的版本信息"""
    return f"""AutoNet4AHU Linux版本 v{VERSION}
构建时间: {BUILD_DATE}
构建系统: {BUILD_SYSTEM}
Python版本: {PYTHON_VERSION}
"""

if __name__ == "__main__":
    print(get_version_info()) 