#!/bin/bash

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置文件和安装目录
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/autonet4ahu"
CONFIG_FILE="${CONFIG_DIR}/config.json"
SYSTEMD_SERVICE_DIR="/etc/systemd/system"
NETWORKMANAGER_HOOK_DIR="/etc/NetworkManager/dispatcher.d"
EXECUTABLE_NAME="autonet4ahu"
EXECUTABLE_PATH="${INSTALL_DIR}/${EXECUTABLE_NAME}"

# 检查是否以root权限运行
check_root() {
    if [ "$(id -u)" != "0" ]; then
        echo -e "${RED}错误: 必须以root权限运行此脚本${NC}"
        echo "请使用 'sudo $0' 重新运行"
        exit 1
    fi
}

# 停止并删除systemd服务
remove_systemd_service() {
    echo -e "${BLUE}移除systemd服务...${NC}"
    
    # 检查systemd是否可用
    if ! command -v systemctl &>/dev/null; then
        echo -e "${YELLOW}系统不支持systemd，跳过服务移除${NC}"
        return
    fi
    
    # 停止并禁用服务和定时器
    systemctl stop autonet4ahu.service 2>/dev/null || true
    systemctl disable autonet4ahu.service 2>/dev/null || true
    systemctl stop autonet4ahu.timer 2>/dev/null || true
    systemctl disable autonet4ahu.timer 2>/dev/null || true
    
    # 删除服务文件
    rm -f "$SYSTEMD_SERVICE_DIR/autonet4ahu.service" 2>/dev/null || true
    rm -f "$SYSTEMD_SERVICE_DIR/autonet4ahu.timer" 2>/dev/null || true
    
    # 重新加载systemd配置
    systemctl daemon-reload 2>/dev/null || true
    
    echo -e "${GREEN}systemd服务已移除${NC}"
}

# 移除NetworkManager钩子
remove_network_manager_hook() {
    echo -e "${BLUE}移除NetworkManager钩子...${NC}"
    
    # 删除钩子脚本
    if [ -f "$NETWORKMANAGER_HOOK_DIR/99-autonet4ahu" ]; then
        rm -f "$NETWORKMANAGER_HOOK_DIR/99-autonet4ahu"
        echo -e "${GREEN}NetworkManager钩子已移除${NC}"
    else
        echo -e "${YELLOW}未找到NetworkManager钩子，跳过${NC}"
    fi
}

# 删除程序文件
remove_program_files() {
    echo -e "${BLUE}删除程序文件...${NC}"
    
    # 询问是否保留配置文件
    read -p "是否保留配置文件? (y/n): " keep_config
    
    # 删除可执行文件
    if [ -f "$EXECUTABLE_PATH" ]; then
        rm -f "$EXECUTABLE_PATH"
        echo -e "${GREEN}可执行文件已删除${NC}"
    else
        echo -e "${YELLOW}可执行文件不存在，跳过${NC}"
    fi
    
    # 根据用户选择删除配置目录
    if [[ "$keep_config" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}保留配置文件: $CONFIG_FILE${NC}"
    else
        if [ -d "$CONFIG_DIR" ]; then
            rm -rf "$CONFIG_DIR"
            echo -e "${GREEN}配置目录已删除${NC}"
        else
            echo -e "${YELLOW}配置目录不存在，跳过${NC}"
        fi
    fi
}

# 清理日志文件
clean_logs() {
    echo -e "${BLUE}清理日志文件...${NC}"
    
    # 清理可能的日志路径
    log_dirs=(
        "/var/log/autonet4ahu"
        "$HOME/.local/share/autonet4ahu/logs"
    )
    
    for log_dir in "${log_dirs[@]}"; do
        if [ -d "$log_dir" ]; then
            rm -rf "$log_dir"
            echo -e "${GREEN}已删除日志目录: $log_dir${NC}"
        fi
    done
    
    # 如果保留了配置目录，也删除里面的日志文件
    if [ -d "$CONFIG_DIR" ]; then
        rm -f "$CONFIG_DIR"/*.log 2>/dev/null || true
    fi
}

# 主函数
main() {
    echo -e "${YELLOW}=== AutoNet4AHU 卸载程序 ===${NC}\n"
    
    # 确认卸载
    read -p "确定要卸载 AutoNet4AHU 吗? (y/n): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}卸载已取消${NC}"
        exit 0
    fi
    
    check_root
    remove_systemd_service
    remove_network_manager_hook
    remove_program_files
    clean_logs
    
    echo -e "\n${GREEN}=== AutoNet4AHU 已成功卸载 ===${NC}\n"
}

main 