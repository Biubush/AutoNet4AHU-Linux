#!/bin/bash

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/../dist"
OUTPUT_NAME="autonet4ahu"

echo -e "${BLUE}开始编译 AutoNet4AHU...${NC}"

# 检查必要的工具
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}错误: pip3 未安装，请先安装 Python3-pip${NC}"
    exit 1
fi

# 安装编译依赖
echo -e "${BLUE}安装编译依赖...${NC}"
pip3 install -r "${SCRIPT_DIR}/requirements.txt" pyinstaller

# 创建输出目录
mkdir -p "${OUTPUT_DIR}"

# 使用PyInstaller打包
echo -e "${BLUE}使用PyInstaller打包...${NC}"
pyinstaller --clean \
    --onefile \
    --name "${OUTPUT_NAME}" \
    --distpath "${OUTPUT_DIR}" \
    --add-data "${SCRIPT_DIR}/requirements.txt:." \
    --hidden-import systemd.journal \
    "${SCRIPT_DIR}/main.py"

# 添加执行权限
chmod +x "${OUTPUT_DIR}/${OUTPUT_NAME}"

echo -e "${GREEN}编译成功: ${OUTPUT_DIR}/${OUTPUT_NAME}${NC}"
echo -e "${BLUE}文件大小: $(du -h "${OUTPUT_DIR}/${OUTPUT_NAME}" | cut -f1)${NC}"

# 清理编译临时文件
echo -e "${BLUE}清理临时文件...${NC}"
rm -rf "${SCRIPT_DIR}/__pycache__" "${SCRIPT_DIR}/build" "${SCRIPT_DIR}/${OUTPUT_NAME}.spec"

echo -e "${GREEN}编译完成!${NC}" 