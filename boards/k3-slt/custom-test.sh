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

# ============================================
# 测试项1: DDR测试 (memtester)
# ============================================
test_event "ddr:start"

if command -v memtester &> /dev/null; then
    # 固定测试1GB内存
    TEST_MEM_MB=1024
    # 运行memtester测试，测试1GB内存，循环1次
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

# 函数：枚举所有 UVC 设备
enumerate_uvc_devices() {
    local uvc_list=()
    for video in /sys/class/video4linux/video*; do
        if [ -f "$video/name" ]; then
            local name=$(cat "$video/name" 2>/dev/null)
            # 过滤掉 ISP/CSI 等板载设备，只保留 UVC
            if echo "$name" | grep -qiE "uvc|usb|capture|hdmi"; then
                if ! echo "$name" | grep -qiE "csi|isp|mvx"; then
                    uvc_list+=("/dev/$(basename $video)")
                fi
            fi
        fi
    done
    echo "${uvc_list[@]}"
}

# 函数：启动 weston 实例
start_weston_for_dp() {
    local dp_device="$1"
    local dp_index="$2"
    local socket_name="wayland-dp${dp_index}"
    
    env MESA_LOADER_DRIVER_OVERRIDE=pvr \
        XDG_RUNTIME_DIR=/root \
        weston --drm-device="$dp_device" \
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

# 函数：在指定 DP 上显示纯色
display_color_on_dp() {
    local dp_index="$1"
    local color="$2"
    local socket_name="wayland-dp${dp_index}"
    local image_file="/tmp/dp${dp_index}_color.bmp"
    
    # 生成纯色图像
    /usr/bin/ffmpeg -hide_banner -loglevel error -y \
        -f lavfi -i "color=c=${color}:s=1920x1080:d=1" \
        -frames:v 1 "$image_file" 2>/dev/null
    
    # 全屏显示
    env XDG_RUNTIME_DIR=/root \
        WAYLAND_DISPLAY="$socket_name" \
        SDL_VIDEODRIVER=wayland \
        /usr/bin/ffplay -hide_banner -loglevel error -fs -loop 0 "$image_file" \
        >/dev/null 2>&1 &
    
    echo $!
}

# 函数：检测 UVC 捕获的图像主色调
detect_dominant_color() {
    local image="$1"
    
    # 使用 ffmpeg 缩放到 1x1 像素获取平均颜色
    local rgb=$(/usr/bin/ffmpeg -hide_banner -loglevel error \
        -i "$image" -vf "scale=1:1" -f rawvideo -pix_fmt rgb24 - 2>/dev/null | \
        od -An -tu1 -N3 | tr -s ' ')
    
    local r=$(echo $rgb | awk '{print $1}')
    local g=$(echo $rgb | awk '{print $2}')
    local b=$(echo $rgb | awk '{print $3}')
    
    # 判断主色调
    if [ $r -gt 200 ] && [ $g -lt 100 ] && [ $b -lt 100 ]; then
        echo "red"
    elif [ $r -lt 100 ] && [ $g -lt 100 ] && [ $b -gt 200 ]; then
        echo "blue"
    elif [ $r -lt 100 ] && [ $g -gt 200 ] && [ $b -lt 100 ]; then
        echo "green"
    elif [ $r -gt 200 ] && [ $g -gt 200 ] && [ $b -lt 100 ]; then
        echo "yellow"
    else
        echo "unknown"
    fi
}

# 主测试流程
DP_DEVICES=($(enumerate_dp_devices))
UVC_DEVICES=($(enumerate_uvc_devices))

if [ ${#DP_DEVICES[@]} -eq 0 ]; then
    test_event "dp:fail:no display connected"
elif [ ${#UVC_DEVICES[@]} -eq 0 ]; then
    test_event "dp:fail:no UVC device found"
else
    # 为每个 DP 启动 weston
    declare -a WESTON_PIDS
    for i in "${!DP_DEVICES[@]}"; do
        if ! weston_pid=$(start_weston_for_dp "${DP_DEVICES[$i]}" "$i"); then
            test_event "dp${i}:fail:weston start failed"
            continue
        fi
        WESTON_PIDS[$i]=$weston_pid
    done
    
    sleep 2  # 等待所有 weston 稳定
    
    # 阶段1: 自动配对
    declare -A DP_UVC_MAP
    declare -a USED_UVC
    COLORS=("red" "blue" "green" "yellow")
    
    for i in "${!DP_DEVICES[@]}"; do
        local dp_device="${DP_DEVICES[$i]}"
        local color="${COLORS[$i]}"
        
        # 显示颜色
        local ffplay_pid=$(display_color_on_dp "$i" "$color")
        sleep 5  # 等待显示稳定
        
        # 遍历 UVC 寻找匹配
        local matched=0
        for uvc in "${UVC_DEVICES[@]}"; do
            # 跳过已配对的 UVC
            if [[ " ${USED_UVC[@]} " =~ " ${uvc} " ]]; then
                continue
            fi
            
            # 捕获一帧
            local capture_file="/tmp/uvc_pair_${i}.bmp"
            /usr/bin/ffmpeg -hide_banner -loglevel error -y \
                -f v4l2 -i "$uvc" -frames:v 1 "$capture_file" 2>/dev/null
            
            if [ -f "$capture_file" ]; then
                local detected_color=$(detect_dominant_color "$capture_file")
                if [ "$detected_color" = "$color" ]; then
                    DP_UVC_MAP["$dp_device"]="$uvc"
                    USED_UVC+=("$uvc")
                    matched=1
                    break
                fi
            fi
        done
        
        kill $ffplay_pid 2>/dev/null
        
        if [ $matched -eq 0 ]; then
            test_event "dp${i}:fail:pairing failed"
        fi
    done
    
    # 阶段2: 正式测试
    for i in "${!DP_DEVICES[@]}"; do
        local dp_device="${DP_DEVICES[$i]}"
        local uvc_device="${DP_UVC_MAP[$dp_device]}"
        
        if [ -z "$uvc_device" ]; then
            test_event "dp${i}:fail:no UVC mapping"
            continue
        fi
        
        test_event "dp${i}:start"
        
        local workdir="/opt/factorytest/res/dp_uvc_compare_${i}"
        mkdir -p "$workdir"
        local temp_output="/tmp/dp${i}_test_output.txt"
        
        # 运行两次测试（预热 + 正式）
        local test_passed=0
        for run in 1 2; do
            env XDG_RUNTIME_DIR=/root \
                WAYLAND_DISPLAY="wayland-dp${i}" \
                SDL_VIDEODRIVER=wayland \
                python3 -u /opt/factorytest/dp_uvc_compare.py \
                    --workdir "$workdir" \
                    --device "$uvc_device" \
                    --threshold 0.90 \
                    > "$temp_output" 2>&1 &
            
            local dp_pid=$!
            
            # 等待最多40秒
            local count=0
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
                break
            fi
            
            # 第二次运行才检查结果
            if [ $run -eq 2 ]; then
                sync
                sleep 1
                if grep -q "result: successful" "$temp_output" 2>/dev/null; then
                    test_event "dp${i}:pass"
                    test_passed=1
                else
                    test_event "dp${i}:fail"
                fi
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
