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

# 详细失败日志函数（只在失败时调用）
test_detail_fail() {
    local test_name="$1"        # 如: ddr, ufs, dp0, dp1
    local test_name_upper=$(echo "$test_name" | tr '[:lower:]' '[:upper:]')
    local reason="$2"
    local log_file="$3"

    local prefix="[DETAIL_FAIL_${test_name_upper}]"

    {
        echo "$prefix ========================================"
        echo "$prefix Test Item: $test_name"
        echo "$prefix Status: FAILED"
        echo "$prefix Chip ID: $CHIP_ID"
        echo "$prefix Error: $reason"
        echo "$prefix ----------------------------------------"
        if [ -f "$log_file" ] && [ -s "$log_file" ]; then
            sed "s/^/$prefix /" "$log_file"
        else
            echo "$prefix (no detailed log available)"
        fi
        echo "$prefix ========================================"
    } | tee -a $LOG_FILE
}

# 开始总测试
test_event "all:start"

# 读取芯片ID (serial number)
CHIP_ID=""
CHIP_ID_FILE="/sys/bus/soc/devices/soc0/serial_number"
if [ -f "$CHIP_ID_FILE" ]; then
    CHIP_ID=$(cat "$CHIP_ID_FILE" 2>/dev/null)
    test_event "chip_id:$CHIP_ID"
else
    CHIP_ID="unknown"
    test_event "chip_id:unknown"
fi

# ============================================
# 测试项1: DDR测试 (memtester) - 后台运行
# ============================================
test_ddr() {
    local ddr_temp_log="/tmp/ddr_combined.log"
    local ddr_event_log="/tmp/ddr_events.log"

    {
        test_event "ddr:start"

        if command -v memtester &> /dev/null; then
            > "$ddr_temp_log"

            # 每个进程测试 10MB 内存，循环 1 次
            TEST_MEM_MB=10
            MEMTESTER_JOBS=4
            declare -a MEMTESTER_PIDS

            for job in $(seq 1 $MEMTESTER_JOBS); do
                memtester ${TEST_MEM_MB}M 1 >> "/tmp/memtester_job${job}.log" 2>&1 &
                MEMTESTER_PIDS[$job]=$!
            done

            DDR_FAIL=0
            for job in $(seq 1 $MEMTESTER_JOBS); do
                if ! wait "${MEMTESTER_PIDS[$job]}"; then
                    DDR_FAIL=1
                fi
                cat "/tmp/memtester_job${job}.log" >> "$ddr_temp_log"
                rm -f "/tmp/memtester_job${job}.log"
            done

            if [ $DDR_FAIL -eq 0 ]; then
                test_event "ddr:pass"
                rm -f "$ddr_temp_log"
            else
                test_event "ddr:fail:memtester failed on one or more jobs"
                test_detail_fail "ddr" "memtester failed on one or more jobs" "$ddr_temp_log"
                rm -f "$ddr_temp_log"
            fi
        else
            test_event "ddr:fail:memtester not found"
        fi
    } > "$ddr_event_log" 2>&1
}

# ============================================
# 测试项2: UFS读写压测 (fio) - 后台运行
# ============================================
test_ufs() {
    local ufs_temp_log="/tmp/ufs_test.log"
    local ufs_event_log="/tmp/ufs_events.log"

    {
        test_event "ufs:start"

        if command -v fio &> /dev/null; then
            > "$ufs_temp_log"

            # 固定使用 /dev/sda 设备
            UFS_DEVICE="/dev/sda"

            if [ -b "$UFS_DEVICE" ]; then
                # 格式化为 ext4 文件系统
                if mkfs.ext4 -F "$UFS_DEVICE" >> "$ufs_temp_log" 2>&1; then
                    # 创建挂载点
                    MOUNT_POINT="/mnt/ufs-test"
                    mkdir -p $MOUNT_POINT

                    # 挂载UFS设备
                    if mount -t ext4 "$UFS_DEVICE" "$MOUNT_POINT" >> "$ufs_temp_log" 2>&1; then
                        # 创建测试文件路径
                        TEST_FILE="$MOUNT_POINT/fio-test-file"

                        # FIO随机混合读写压测 (50%读 + 50%写)
                        if fio --name=randrw --filename=$TEST_FILE --rw=randrw --bs=4k \
                            --size=50M --numjobs=4 --iodepth=16 --runtime=15 --time_based --direct=1 \
                            --output-format=normal >> "$ufs_temp_log" 2>&1; then
                            test_event "ufs:pass"
                            rm -f "$ufs_temp_log"
                        else
                            EXIT_CODE=$?
                            test_event "ufs:fail:fio exit code $EXIT_CODE"
                            test_detail_fail "ufs" "fio exit code $EXIT_CODE" "$ufs_temp_log"
                            rm -f "$ufs_temp_log"
                        fi

                        # 清理测试文件
                        rm -f $TEST_FILE

                        # 卸载设备
                        umount $MOUNT_POINT >> "$ufs_temp_log" 2>&1
                    else
                        test_event "ufs:fail:mount failed"
                        test_detail_fail "ufs" "mount failed" "$ufs_temp_log"
                        rm -f "$ufs_temp_log"
                    fi

                    # 清理挂载点
                    rmdir $MOUNT_POINT 2>/dev/null || true
                else
                    test_event "ufs:fail:format failed"
                    test_detail_fail "ufs" "format failed" "$ufs_temp_log"
                    rm -f "$ufs_temp_log"
                fi
            else
                test_event "ufs:fail:device not found"
                rm -f "$ufs_temp_log"
            fi
        else
            test_event "ufs:fail:fio not found"
        fi
    } > "$ufs_event_log" 2>&1
}

# ============================================
# 测试项3: DP测试 (dp_uvc_compare) - 后台运行
# ============================================

# DP-UVC 静态设备映射配置
declare -A DP_UVC_DEVICE_MAP=(
    ["card1-DP-1"]="/dev/v4l/by-path/platform-xhci-hcd.3.auto-usb-0:1:1.0-video-index0" # dp0
    ["card2-DP-2"]="/dev/v4l/by-path/platform-xhci-hcd.2.auto-usb-0:1:1.0-video-index0" # dp1
)

# 本板期望测试的DP接口
DP_CONNECTOR_ORDER=("card1-DP-1" "card2-DP-2")

# 函数：读取指定DP连接器的HPD状态
get_dp_status() {
    local status_file="/sys/class/drm/$1/status"
    if [ -f "$status_file" ]; then
        cat "$status_file" 2>/dev/null
    else
        echo "not_found"
    fi
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

# 测试单个DP的函数
test_single_dp() {
    local dp_index="$1"
    local dp_device="${DP_CONNECTOR_ORDER[$dp_index]}"
    local dp_event_log="/tmp/dp${dp_index}_events.log"
    local weston_pid=""

    {
        dp_status=$(get_dp_status "$dp_device")
        if [ "$dp_status" != "connected" ]; then
            test_event "dp${dp_index}:fail:${dp_device} not connected (status=${dp_status})"
            test_event "dp${dp_index}:end"
            return 1
        fi

        # 通过静态配置查找对应 UVC 设备
        uvc_device="${DP_UVC_DEVICE_MAP[$dp_device]}"
        if [ -z "$uvc_device" ] || [ ! -e "$uvc_device" ]; then
            test_event "dp${dp_index}:fail:UVC device not found: $uvc_device"
            test_event "dp${dp_index}:end"
            return 1
        fi

        # 启动 weston
        if ! weston_pid=$(start_weston_for_dp "$dp_device" "$dp_index"); then
            test_event "dp${dp_index}:fail:weston start failed"
            test_event "dp${dp_index}:end"
            return 1
        fi

        test_event "dp${dp_index}:start"

        workdir="/opt/factorytest/res/dp_uvc_compare_${dp_index}"
        mkdir -p "$workdir"
        temp_output="/tmp/dp${dp_index}_test_output.txt"

        # 运行两次（预热 + 正式）
        for run in 1 2; do
            env XDG_RUNTIME_DIR=/root \
                WAYLAND_DISPLAY="wayland-dp${dp_index}" \
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
                test_event "dp${dp_index}:fail:timeout on run $run"
                test_detail_fail "dp${dp_index}" "timeout on run $run" "$temp_output"
                test_event "dp${dp_index}:end"
                rm -f "$temp_output"
                kill $weston_pid 2>/dev/null || true
                return 1
            fi

            if [ $run -eq 2 ]; then
                sync
                sleep 1
                if grep -q "result: successful" "$temp_output" 2>/dev/null; then
                    test_event "dp${dp_index}:pass"
                    rm -f "$temp_output"
                else
                    test_event "dp${dp_index}:fail"
                    test_detail_fail "dp${dp_index}" "comparison failed" "$temp_output"
                    rm -f "$temp_output"
                fi
                test_event "dp${dp_index}:end"
            fi
        done

        # 清理 weston 进程
        kill $weston_pid 2>/dev/null || true

    } > "$dp_event_log" 2>&1
}

# ============================================
# 启动所有测试项（并行）
# ============================================

# 启动DDR测试（后台）
test_ddr &
DDR_PID=$!

# 启动UFS测试（后台）
test_ufs &
UFS_PID=$!

# 启动DP0测试（后台）
test_single_dp 0 &
DP0_PID=$!

# 启动DP1测试（后台）
test_single_dp 1 &
DP1_PID=$!

# ============================================
# 等待所有测试完成并收集结果
# ============================================

# 等待所有后台进程完成
wait $DDR_PID
wait $UFS_PID
wait $DP0_PID
wait $DP1_PID

# 按顺序合并测试结果到主日志
if [ -f "/tmp/ddr_events.log" ]; then
    cat "/tmp/ddr_events.log" >> $LOG_FILE
    rm -f "/tmp/ddr_events.log"
fi

if [ -f "/tmp/ufs_events.log" ]; then
    cat "/tmp/ufs_events.log" >> $LOG_FILE
    rm -f "/tmp/ufs_events.log"
fi

if [ -f "/tmp/dp0_events.log" ]; then
    cat "/tmp/dp0_events.log" >> $LOG_FILE
    rm -f "/tmp/dp0_events.log"
fi

if [ -f "/tmp/dp1_events.log" ]; then
    cat "/tmp/dp1_events.log" >> $LOG_FILE
    rm -f "/tmp/dp1_events.log"
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
