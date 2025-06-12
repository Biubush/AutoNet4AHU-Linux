#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BINARY_PATH="$1"

if [ -z "$BINARY_PATH" ]; then
    echo -e "${RED}错误: 请提供二进制文件路径${NC}"
    echo "用法: $0 <二进制文件路径>"
    exit 1
fi

if [ ! -f "$BINARY_PATH" ]; then
    echo -e "${RED}错误: 文件 '$BINARY_PATH' 不存在${NC}"
    exit 1
fi

echo -e "${BLUE}检查系统中的libsystemd...${NC}"

# 检查系统是否有libsystemd
if ldconfig -p | grep -q libsystemd; then
    echo -e "${GREEN}系统已安装libsystemd，无需修补${NC}"
    exit 0
fi

# 检查是否有patchelf工具
if ! command -v patchelf &> /dev/null; then
    echo -e "${YELLOW}未找到patchelf工具，尝试安装...${NC}"
    
    # 尝试安装patchelf
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y patchelf
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y patchelf
    elif command -v yum &> /dev/null; then
        sudo yum install -y patchelf
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm patchelf
    else
        echo -e "${RED}无法安装patchelf，请手动安装后再运行此脚本${NC}"
        exit 1
    fi
fi

# 再次检查patchelf是否可用
if ! command -v patchelf &> /dev/null; then
    echo -e "${RED}patchelf安装失败，无法继续${NC}"
    exit 1
fi

echo -e "${BLUE}修补二进制文件...${NC}"

# 创建备份
cp "$BINARY_PATH" "${BINARY_PATH}.bak"
echo -e "${BLUE}已创建备份: ${BINARY_PATH}.bak${NC}"

# 使用patchelf移除libsystemd依赖
patchelf --remove-needed libsystemd.so.0 "$BINARY_PATH"

echo -e "${GREEN}二进制文件已修补完成${NC}"
echo -e "${YELLOW}注意: 修补后的程序将不支持systemd日志功能，但基本功能不受影响${NC}"

exit 0 