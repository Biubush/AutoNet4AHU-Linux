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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
EXECUTABLE_NAME="autonet4ahu"
EXECUTABLE_PATH="${INSTALL_DIR}/${EXECUTABLE_NAME}"
BINARY_PATH="${PARENT_DIR}/dist/${EXECUTABLE_NAME}"

# 检查是否以root权限运行
check_root() {
    if [ "$(id -u)" != "0" ]; then
        echo -e "${RED}错误: 必须以root权限运行此脚本${NC}"
        echo "请使用 'sudo $0' 重新运行"
        exit 1
    fi
}

# 检测系统类型和版本
detect_system() {
    if [ -f /etc/os-release ]; then
        # 加载系统信息
        . /etc/os-release
        OS=$NAME
        VERSION=$VERSION_ID
        echo -e "${BLUE}检测到系统: $OS $VERSION${NC}"
    else
        echo -e "${YELLOW}警告: 无法检测系统类型，将尝试通用安装${NC}"
        OS="Unknown"
        VERSION="Unknown"
    fi
    
    # 检查Python版本
    if command -v python3 &>/dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        echo -e "${BLUE}检测到Python版本: $PYTHON_VERSION${NC}"
    else
        echo -e "${RED}错误: 系统未安装Python 3${NC}"
        echo "请先安装Python 3"
        exit 1
    fi
}

# 安装依赖
install_dependencies() {
    echo -e "${BLUE}检查系统依赖...${NC}"
    
    # 根据不同的系统类型安装基础依赖
    case "$OS" in
        "Ubuntu" | "Debian" | "Kali"*)
            apt-get update
            apt-get install -y libsystemd-dev
            ;;
        "CentOS" | "Fedora" | "Red Hat"*)
            if command -v dnf &>/dev/null; then
                dnf install -y systemd-devel
            else
                yum install -y systemd-devel
            fi
            ;;
        "Arch"*)
            pacman -Sy libsystemd --noconfirm
            ;;
        *)
            echo -e "${YELLOW}未知系统类型，跳过依赖安装${NC}"
            ;;
    esac
    
    echo -e "${GREEN}依赖检查完成${NC}"
}

# 复制程序文件
copy_program_files() {
    echo -e "${BLUE}安装程序文件...${NC}"
    
    # 创建配置目录
    mkdir -p "$CONFIG_DIR"
    
    # 检查二进制文件是否存在
    if [ -f "$BINARY_PATH" ]; then
        # 复制二进制文件
        cp "$BINARY_PATH" "$EXECUTABLE_PATH"
        chmod 755 "$EXECUTABLE_PATH"
        echo -e "${GREEN}已安装可执行文件: $EXECUTABLE_PATH${NC}"
        
        # 检查系统是否有libsystemd，如果没有则尝试修补二进制文件
        if ! ldconfig -p 2>/dev/null | grep -q libsystemd; then
            echo -e "${YELLOW}系统未安装libsystemd，尝试修补二进制文件...${NC}"
            if [ -f "${SCRIPT_DIR}/patch_binary.sh" ]; then
                bash "${SCRIPT_DIR}/patch_binary.sh" "$EXECUTABLE_PATH"
            else
                echo -e "${YELLOW}未找到patch_binary.sh脚本，跳过修补${NC}"
                echo -e "${YELLOW}注意：如果运行时出现libsystemd相关错误，请安装libsystemd-dev(Debian/Ubuntu)或systemd-devel(RHEL/CentOS)${NC}"
            fi
        fi
    else
        echo -e "${RED}错误: 找不到二进制文件 $BINARY_PATH${NC}"
        echo -e "${YELLOW}请先运行: bash ${PARENT_DIR}/loginCore/build.sh${NC}"
        exit 1
    fi
    
    # 复制配置文件模板（如果不存在）
    if [ ! -f "$CONFIG_FILE" ]; then
        if [ -f "$PARENT_DIR/config.json" ]; then
            cp "$PARENT_DIR/config.json" "$CONFIG_FILE"
        elif [ -f "$PARENT_DIR/config.json.template" ]; then
            cp "$PARENT_DIR/config.json.template" "$CONFIG_FILE"
        else
            echo -e "${RED}错误: 找不到配置文件模板${NC}"
            exit 1
        fi
        echo -e "${YELLOW}已创建配置文件模板，请编辑: $CONFIG_FILE${NC}"
    else
        echo -e "${BLUE}配置文件已存在，跳过复制${NC}"
    fi
    
    echo -e "${GREEN}程序文件安装完成${NC}"
}

# 创建systemd服务
create_systemd_service() {
    echo -e "${BLUE}创建systemd服务...${NC}"
    
    # 检查systemd是否可用
    if ! command -v systemctl &>/dev/null; then
        echo -e "${YELLOW}系统不支持systemd，跳过服务创建${NC}"
        return
    fi
    
    # 创建服务文件
    cat > "$SYSTEMD_SERVICE_DIR/autonet4ahu.service" << EOF
[Unit]
Description=AutoNet4AHU - 安徽大学校园网自动登录
After=network.target
Wants=autonet4ahu.timer

[Service]
Type=simple
ExecStart=$EXECUTABLE_PATH -c $CONFIG_FILE login
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # 创建定时器文件
    cat > "$SYSTEMD_SERVICE_DIR/autonet4ahu.timer" << EOF
[Unit]
Description=AutoNet4AHU Timer - 定期检查校园网连接
After=network.target

[Timer]
OnBootSec=60
OnUnitActiveSec=300
AccuracySec=30

[Install]
WantedBy=timers.target
EOF

    # 重新加载systemd配置
    systemctl daemon-reload
    
    # 启用并启动服务和定时器
    systemctl enable autonet4ahu.service
    systemctl enable autonet4ahu.timer
    systemctl start autonet4ahu.timer
    
    echo -e "${GREEN}systemd服务创建并启动完成${NC}"
}

# 创建NetworkManager钩子
create_network_manager_hook() {
    echo -e "${BLUE}创建NetworkManager钩子...${NC}"
    
    # 检查NetworkManager是否可用
    if ! command -v nmcli &>/dev/null; then
        echo -e "${YELLOW}系统未安装NetworkManager，跳过钩子创建${NC}"
        return
    fi
    
    # 创建钩子脚本
    mkdir -p "$NETWORKMANAGER_HOOK_DIR"
    
    cat > "$NETWORKMANAGER_HOOK_DIR/99-autonet4ahu" << EOF
#!/bin/bash

INTERFACE="\$1"
STATUS="\$2"

# 仅在网络连接时触发
if [ "\$STATUS" = "up" ] || [ "\$STATUS" = "connectivity-change" ]; then
    logger -t autonet4ahu "网络接口 \$INTERFACE 状态变为 \$STATUS，尝试登录校园网"
    $EXECUTABLE_PATH -c $CONFIG_FILE login
fi

exit 0
EOF

    # 设置执行权限
    chmod 755 "$NETWORKMANAGER_HOOK_DIR/99-autonet4ahu"
    
    echo -e "${GREEN}NetworkManager钩子创建完成${NC}"
}

# 提示配置文件设置
prompt_config() {
    echo -e "\n${YELLOW}安装完成，但您需要设置您的账号信息${NC}"
    echo -e "请编辑配置文件: ${BLUE}$CONFIG_FILE${NC}"
    echo -e "配置示例:"
    echo -e "${GREEN}{
    \"student_id\": \"您的学号\",
    \"password\": \"您的密码\",
    \"webhook_urls\": [\"可选的企业微信webhook地址\"],
    \"log_level\": \"INFO\"
}${NC}\n"

    # 询问是否现在编辑配置文件
    read -p "是否现在编辑配置文件? (y/n): " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        if command -v nano &>/dev/null; then
            nano "$CONFIG_FILE"
        elif command -v vim &>/dev/null; then
            vim "$CONFIG_FILE"
        else
            echo -e "${YELLOW}未找到编辑器，请稍后手动编辑配置文件${NC}"
        fi
    fi
}

# 显示安装完成信息
show_completion_info() {
    echo -e "\n${GREEN}=== AutoNet4AHU 安装完成 ===${NC}\n"
    echo -e "系统服务状态:"
    if command -v systemctl &>/dev/null; then
        systemctl status autonet4ahu.service --no-pager || true
        echo -e "\n定时器状态:"
        systemctl status autonet4ahu.timer --no-pager || true
    fi
    
    echo -e "\n${BLUE}使用以下命令检查登录状态:${NC}"
    echo -e "  ${GREEN}systemctl status autonet4ahu.service${NC}"
    echo -e "  ${GREEN}journalctl -u autonet4ahu.service${NC}"
    
    echo -e "\n${BLUE}手动运行登录命令:${NC}"
    echo -e "  ${GREEN}python3 $EXECUTABLE_PATH -c $CONFIG_FILE login${NC}"
    
    echo -e "\n${BLUE}如需卸载，请运行:${NC}"
    echo -e "  ${GREEN}sudo $(dirname "$0")/uninstall.sh${NC}\n"
}

# 主函数
main() {
    echo -e "${GREEN}=== AutoNet4AHU 安装程序 ===${NC}\n"
    
    check_root
    detect_system
    install_dependencies
    copy_program_files
    create_systemd_service
    create_network_manager_hook
    prompt_config
    show_completion_info
}

main 