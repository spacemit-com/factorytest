#!/bin/bash

LOG_FILE=/var/log/k3-slt-evb-test.log

# 清空日志文件
> $LOG_FILE

# 设置内核日志等级为4 (WARNING级别)
echo 4 > /proc/sys/kernel/printk

# 测试事件函数
test_event() {
    printf "TEST_EVENT:%s\n" "$*" | tee -a $LOG_FILE
}

# 开始总测试
test_event "all:start"

# 读取芯片ID (serial number)
CHIP_ID_FILE="/sys/bus/soc/devices/soc0/serial_number"
if [ -f "$CHIP_ID_FILE" ]; then
    CHIP_ID=$(cat "$CHIP_ID_FILE" 2>/dev/null)
    test_event "chip_id:$CHIP_ID"
else
    test_event "chip_id:unknown"
fi

# ============================================
# 测试项1: DDR测试 (memtester)
# ============================================
test_event "ddr:start"

if command -v memtester &> /dev/null; then
    # 缩短测试时长：只测试 512MB 内存，循环 1 次
    TEST_MEM_MB=512
    # 运行memtester测试，测试 512MB 内存，循环 1 次
    if memtester ${TEST_MEM_MB}M 1 >> $LOG_FILE 2>&1; then
        test_event "ddr:pass"
    else
        EXIT_CODE=$?
        test_event "ddr:fail:memtester exit code $EXIT_CODE"
    fi
else
    test_event "ddr:fail:memtester not found"
fi

# ============================================
# 测试项2: UFS读写压测 (fio)
# ============================================
test_event "ufs:start"

if command -v fio &> /dev/null; then
    # 固定使用 /dev/sda 设备
    UFS_DEVICE="/dev/sda"

    if [ -b "$UFS_DEVICE" ]; then
        # 格式化为 ext4 文件系统
        if mkfs.ext4 -F "$UFS_DEVICE" >> $LOG_FILE 2>&1; then
            # 创建挂载点
            MOUNT_POINT="/mnt/ufs-test"
            mkdir -p $MOUNT_POINT
            
            # 挂载UFS设备
            if mount -t ext4 "$UFS_DEVICE" "$MOUNT_POINT" >> $LOG_FILE 2>&1; then
                # 创建测试文件路径
                TEST_FILE="$MOUNT_POINT/fio-test-file"
                
                # FIO随机混合读写压测 (50%读 + 50%写)
                if fio --name=randrw --filename=$TEST_FILE --rw=randrw --bs=4k \
                    --size=100M --numjobs=4 --iodepth=16 --runtime=60 --time_based --direct=1 \
                    --output-format=normal >> $LOG_FILE 2>&1; then
                    test_event "ufs:pass"
                else
                    EXIT_CODE=$?
                    test_event "ufs:fail:fio exit code $EXIT_CODE"
                fi
                
                # 清理测试文件
                rm -f $TEST_FILE
                
                # 卸载设备
                umount $MOUNT_POINT >> $LOG_FILE 2>&1
            else
                test_event "ufs:fail:mount failed"
            fi
            
            # 清理挂载点
            rmdir $MOUNT_POINT 2>/dev/null || true
        else
            test_event "ufs:fail:format failed"
        fi
    else
        test_event "ufs:fail:device not found"
    fi
else
    test_event "ufs:fail:fio not found"
fi

# ============================================
# 测试项3: DP测试 (dp_uvc_compare)
# ============================================

# ============================================
# DP-UVC 静态设备映射配置
# 在板子上运行 ls -l /dev/v4l/by-path/ 查看稳定的设备符号链接
# 格式: ["DRM连接器名"]="UVC设备路径"
# 注意：当只有一个采集卡时，两个 DP 共用同一个 UVC 设备（按顺序测试）
declare -A DP_UVC_DEVICE_MAP=(
    ["card1-DP-1"]="/dev/v4l/by-path/platform-xhci-hcd.3.auto-usb-0:1:1.0-video-index0"
    ["card2-DP-2"]="/dev/v4l/by-path/platform-xhci-hcd.2.auto-usb-0:1:1.0-video-index0"
)
# 如果有两个采集卡，将第二个 DP 映射到第二个采集卡路径即可
# ============================================

# 函数：枚举所有 connected 的 DP 接口
enumerate_dp_devices() {
    local dp_list=()
    for drm_dir in /sys/class/drm/card*-DP-*; do
        if [ -f "$drm_dir/status" ]; then
            STATUS=$(cat "$drm_dir/status" 2>/dev/null)
            if [ "$STATUS" = "connected" ]; then
                local device=$(basename "$drm_dir")
                dp_list+=("$device")
            fi
        fi
    done
    echo "${dp_list[@]}"
}

# 函数：启动 weston 实例
start_weston_for_dp() {
    local dp_device="$1"
    local dp_index="$2"
    local socket_name="wayland-dp${dp_index}"
    local card_name=$(echo "$dp_device" | grep -o 'card[0-9]*')
    
    env MESA_LOADER_DRIVER_OVERRIDE=pvr \
        XDG_RUNTIME_DIR=/root \
        weston --drm-device="$card_name" \
        --socket="$socket_name" \
        --idle-time=0 \
        --log="/var/log/weston-dp${dp_index}.log" \
        >/dev/null 2>&1 &
    
    local weston_pid=$!
    
    # 等待 socket 就绪（最多10秒）
    local wait_count=0
    while [ ! -e "/root/$socket_name" ] && [ $wait_count -lt 100 ]; do
        sleep 0.1
        wait_count=$((wait_count + 1))
    done
    
    if [ -e "/root/$socket_name" ]; then
        echo "$weston_pid"
        return 0
    else
        kill $weston_pid 2>/dev/null
        return 1
    fi
}

# 主测试流程
DP_DEVICES=($(enumerate_dp_devices))

if [ ${#DP_DEVICES[@]} -eq 0 ]; then
    test_event "dp:fail:no display connected"
else
    declare -a WESTON_PIDS
    
    for i in "${!DP_DEVICES[@]}"; do
        dp_device="${DP_DEVICES[$i]}"
        
        # 通过静态配置查找对应 UVC 设备
        uvc_device="${DP_UVC_DEVICE_MAP[$dp_device]}"
        if [ -z "$uvc_device" ] || [ ! -e "$uvc_device" ]; then
            test_event "dp${i}:fail:UVC device not found: $uvc_device"
            continue
        fi
        
        # 启动 weston
        if ! weston_pid=$(start_weston_for_dp "$dp_device" "$i"); then
            test_event "dp${i}:fail:weston start failed"
            continue
        fi
        WESTON_PIDS[$i]=$weston_pid
        
        test_event "dp${i}:start"
        
        workdir="/opt/factorytest/res/dp_uvc_compare_${i}"
        mkdir -p "$workdir"
        temp_output="/tmp/dp${i}_test_output.txt"
        
        # 运行两次（预热 + 正式）
        for run in 1 2; do
            env XDG_RUNTIME_DIR=/root \
                WAYLAND_DISPLAY="wayland-dp${i}" \
                SDL_VIDEODRIVER=wayland \
                python3 -u /opt/factorytest/dp_uvc_compare.py \
                    --workdir "$workdir" \
                    --device "$uvc_device" \
                    --threshold 0.90 \
                    > "$temp_output" 2>&1 &
            
            dp_pid=$!
            count=0
            while [ $count -lt 40 ]; do
                if ! kill -0 $dp_pid 2>/dev/null; then
                    break
                fi
                sleep 1
                count=$((count + 1))
            done
            
            wait $dp_pid 2>/dev/null || true
            
            if [ $count -eq 40 ]; then
                kill -9 $dp_pid 2>/dev/null
                test_event "dp${i}:fail:timeout on run $run"
                test_event "dp${i}:end"
                break
            fi
            
            if [ $run -eq 2 ]; then
                sync
                sleep 1
                if grep -q "result: successful" "$temp_output" 2>/dev/null; then
                    test_event "dp${i}:pass"
                else
                    test_event "dp${i}:fail"
                fi
                test_event "dp${i}:end"
            fi
        done
    done
    
    # 清理 weston 进程
    for pid in "${WESTON_PIDS[@]}"; do
        kill $pid 2>/dev/null || true
    done
fi

# ============================================
# 在这里添加更多测试项
# ============================================

# 测试项模板：
# test_event "testname:start"
# if your_test_command; then
#     test_event "testname:pass"
# else
#     test_event "testname:fail:error message"
# fi

# 结束总测试
test_event "all:end"
