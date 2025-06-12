# AutoNet4AHU - 安徽大学校园网自动登录工具 (Linux版)

这是一个用于安徽大学校园网自动登录的工具，可以在网络连接时自动进行校园网认证，避免手动登录的麻烦。

Author: [Biubush](https://github.com/biubush) from [AHU](https://www.ahu.edu.cn/)

## 目录

- [项目特点](#项目特点)
- [系统要求](#系统要求)
- [项目结构](#项目结构)
  - [登录核心模块](#1-登录核心模块-logincore)
  - [自动化脚本](#2-自动化脚本-scripts)
  - [发布与部署](#3-发布与部署)
- [技术栈](#技术栈)
- [使用方法](#使用方法)
  - [二进制安装（推荐）](#二进制安装)
  - [卸载](#卸载)
  - [手动运行](#手动运行)
- [配置文件说明](#配置文件说明)
- [企业微信通知配置](#企业微信通知配置)
- [自动化触发原理](#自动化触发原理)
- [开发指南](#开发指南)
  - [从源码编译（仅开发用途）](#从源码编译)
  - [创建发布](#创建发布)
- [常见问题](#常见问题)
- [注意事项](#注意事项)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 项目特点

- **支持多种Linux发行版，兼容性广泛**
- **提供预编译的二进制文件，无需配置Python环境**
- **提供systemd服务和NetworkManager钩子脚本，实现高效的自动登录**
- **纯命令行操作，适合服务器环境和远程管理**
- **自动创建系统服务，实现网络连接时自动登录**
- **用户数据本地私有化，确保数据安全**
- **支持企业微信webhook通知功能，可以接收登录状态通知**
- **轻量级设计，资源占用少**
- **全面的异常处理机制，确保稳定运行**
- **自动化构建和发布流程，方便维护和升级**

## 系统要求

- Linux操作系统（已在以下系统测试通过）:
  - Ubuntu 18.04+
  - Debian 10+
  - CentOS 7+
  - Fedora 30+
  - Arch Linux
- 使用二进制安装时无特殊要求
- 使用源码安装时需要Python 3.6+

## 项目结构

项目主要分为三个主要模块：

### 1. 登录核心模块 (loginCore)

核心功能实现，包括：

- `main.py` - 主程序入口，处理配置加载和登录流程
- `portal.py` - 实现校园网ePortal登录功能
- `notify.py` - 通知模块，实现企业微信webhook消息推送
- `version.py` - 版本信息管理
- `requirements.txt` - 核心模块依赖列表
- `build.sh` - 编译脚本，将Python代码打包为二进制文件

### 2. 自动化脚本 (scripts)

实现自动化部署和系统集成：

- `install.sh` - 安装脚本，配置服务和网络钩子
- `uninstall.sh` - 卸载脚本，移除相关服务和钩子
- `network-manager-hook.sh` - NetworkManager网络连接钩子脚本
- `autonet4ahu.service` - systemd服务文件
- `autonet4ahu.timer` - systemd定时器文件，用于周期性检查

### 3. 发布与部署

使用GitHub Actions自动化构建和发布流程：

- `.github/workflows/release.yml` - GitHub Actions工作流配置
- `dist/` - 编译输出目录，包含编译后的二进制文件

## 技术栈

- **自动登录核心**: Python，使用requests库进行HTTP请求，编译为独立二进制文件
- **自动化机制**: systemd服务、NetworkManager钩子
- **通知功能**: 企业微信webhook机器人API
- **日志系统**: Python logging模块，syslog集成
- **部署工具**: Shell脚本，自动适配不同发行版
- **自动化构建**: GitHub Actions，PyInstaller

## 使用方法

### 二进制安装（推荐）

使用预编译的二进制文件进行安装，无需配置Python环境：

1. 前往[Releases页面](https://github.com/biubush/AutoNet4AHU-Linux/releases)下载最新版本
2. 解压下载的压缩包
```bash
tar -zxvf autonet4ahu-linux.tar.gz
```
3. 运行安装脚本
```bash
sudo ./scripts/install.sh
```
4. 编辑配置文件
```bash
sudo nano /etc/autonet4ahu/config.json
```

### 卸载

```bash
sudo ./scripts/uninstall.sh
```

### 手动运行

```bash
/usr/local/bin/autonet4ahu -c /etc/autonet4ahu/config.json login
```

## 配置文件说明

配置文件`config.json`包含以下字段：

- `student_id`: 学号
- `password`: 密码
- `webhook_urls`: 企业微信webhook URL列表，用于接收登录通知
- `log_level`: 日志级别（DEBUG, INFO, WARNING, ERROR）

配置文件示例：
```json
{
    "student_id": "S25xxxxxxx",
    "password": "your_password",
    "webhook_urls": [
        "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx"
    ],
    "log_level": "INFO"
}
```

## 企业微信通知配置

要使用企业微信通知功能：

1. 在企业微信应用中创建一个群聊机器人
2. 复制机器人的Webhook URL
3. 将该URL填入配置文件中
4. 登录成功后，机器人将推送登录状态通知到群聊

详细说明请参考[企业微信文档](https://open.work.weixin.qq.com/help2/pc/14931#%E5%85%AD%E3%80%81%E7%BE%A4%E6%9C%BA%E5%99%A8%E4%BA%BAWebhook%E5%9C%B0%E5%9D%80)

## 自动化触发原理

本项目提供两种自动触发机制，确保兼容性和可靠性：

1. **NetworkManager钩子脚本**：当网络连接或变更时自动触发登录
2. **systemd定时服务**：定期检查网络状态，确保连接持续有效

无论使用哪种触发方式，系统都将在网络可用时尝试登录校园网，实现无人值守自动化。

## 开发指南

### 从源码编译（仅开发用途）

如果您是开发者，可以从源码编译二进制文件：

1. 克隆仓库
```bash
git clone https://github.com/biubush/AutoNet4AHU-Linux.git
cd AutoNet4AHU-Linux
```

2. 安装依赖
```bash
pip3 install -r loginCore/requirements.txt pyinstaller
```

3. 编译二进制文件
```bash
cd loginCore
bash build.sh
```

编译后的可执行文件将保存在 `dist/` 目录中。

### 创建发布

项目使用GitHub Actions自动化构建和发布流程。要创建新的发布版本：

1. 创建一个以`v`开头的新标签，如`v1.0.1`
```bash
git tag v1.0.1
git push origin v1.0.1
```

2. GitHub Actions会自动触发构建流程，编译二进制文件并创建发布
3. 发布说明中会自动包含从上个版本以来的所有提交信息

## 常见问题

- **登录失败**：请检查学号和密码是否正确
- **服务无法启动**：检查配置文件路径和权限
- **通知未收到**：检查webhook URL是否正确，网络是否正常
- **无法自动触发**：检查NetworkManager是否正常运行，或systemd服务是否启用
- **安装脚本报错**：检查是否有合适的权限，或尝试手动安装

## 注意事项

- 本工具仅适用于安徽大学校园网环境
- 账号密码保存在本地配置文件中，请确保系统安全
- 如遇校园网认证系统更新，可能需要更新本工具
- 请根据自己实际使用的Linux发行版调整相关配置

## 贡献指南

欢迎提交Issue和Pull Request帮助改进此项目。

## 许可证

该项目采用MIT许可证发布。 