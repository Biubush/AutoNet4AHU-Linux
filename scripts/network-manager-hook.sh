#!/bin/bash

# NetworkManager钩子脚本，在网络连接事件时自动登录校园网
# 此脚本将被安装到 /etc/NetworkManager/dispatcher.d/

# 获取接口和状态
INTERFACE="$1"
STATUS="$2"

# 配置文件路径
CONFIG_FILE="/etc/autonet4ahu/config.json"
PROGRAM_PATH="/usr/local/bin/autonet4ahu/main.py"
LOG_FILE="/var/log/autonet4ahu/network-hook.log"

# 确保日志目录存在
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

# 记录日志的函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    logger -t "autonet4ahu" "$1"
}

# 检查是否为无线或有线接口
is_network_interface() {
    if [[ "$INTERFACE" == wlan* ]] || [[ "$INTERFACE" == eth* ]] || [[ "$INTERFACE" == enp* ]] || [[ "$INTERFACE" == wlp* ]]; then
        return 0  # 0表示真
    else
        return 1  # 1表示假
    fi
}

# 仅在网络连接或连通性变化时触发
if [ "$STATUS" = "up" ] || [ "$STATUS" = "connectivity-change" ]; then
    # 检查接口类型
    if is_network_interface; then
        log "网络接口 $INTERFACE 状态变为 $STATUS，尝试登录校园网"
        
        # 等待几秒钟确保网络稳定
        sleep 2
        
        # 确保程序和配置文件存在
        if [ -f "$PROGRAM_PATH" ] && [ -f "$CONFIG_FILE" ]; then
            # 执行登录程序
            log "执行登录程序: $PROGRAM_PATH -c $CONFIG_FILE login"
            output=$(/usr/bin/python3 "$PROGRAM_PATH" -c "$CONFIG_FILE" login 2>&1)
            exit_code=$?
            
            # 记录执行结果
            if [ $exit_code -eq 0 ]; then
                log "登录成功: $output"
            else
                log "登录失败 (代码 $exit_code): $output"
            fi
        else
            log "错误: 程序文件或配置文件不存在"
            log "程序路径: $PROGRAM_PATH ($([ -f "$PROGRAM_PATH" ] && echo "存在" || echo "不存在"))"
            log "配置文件: $CONFIG_FILE ($([ -f "$CONFIG_FILE" ] && echo "存在" || echo "不存在"))"
        fi
    else
        log "忽略非常规网络接口: $INTERFACE"
    fi
else
    # 在调试模式下记录所有事件
    log "收到事件: 接口=$INTERFACE, 状态=$STATUS (不触发登录)"
fi

exit 0 