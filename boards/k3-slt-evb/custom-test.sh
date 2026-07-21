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
    # 检查UFS设备是否存在
    UFS_DEVICE="/dev/sda3"
    
    # 尝试多个可能的UFS设备路径
    if [ ! -b "$UFS_DEVICE" ]; then
        for dev in /dev/sda /dev/sdb /dev/mmcblk0 /dev/nvme0n1; do
            if [ -b "$dev" ]; then
                UFS_DEVICE="$dev"
                break
            fi
        done
    fi
    
    if [ -b "$UFS_DEVICE" ]; then
        # 创建挂载点
        MOUNT_POINT="/mnt/ufs-test"
        mkdir -p $MOUNT_POINT
        
        # 挂载UFS设备
        if mount $UFS_DEVICE $MOUNT_POINT >> $LOG_FILE 2>&1; then
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
        test_event "ufs:fail:no storage device found"
    fi
else
    test_event "ufs:fail:fio not found"
fi

# ============================================
# 测试项3: DP测试 (dp_uvc_compare)
# ============================================
test_event "dp:start"

# 检查显示器是否连接
DISPLAY_CONNECTED=0
for status_file in /sys/class/drm/card*/status; do
    if [ -f "$status_file" ]; then
        STATUS=$(cat "$status_file" 2>/dev/null)
        if [ "$STATUS" = "connected" ]; then
            DISPLAY_CONNECTED=1
            break
        fi
    fi
done

if [ $DISPLAY_CONNECTED -eq 0 ]; then
    test_event "dp:fail:display not connected"
else
    # 检查并清空/重建工作目录
    WORKDIR="/opt/factorytest/res/dp_uvc_compare"
    if [ -d "$WORKDIR" ]; then
        # 目录存在，清空内容
        rm -rf $WORKDIR/*
    else
        # 目录不存在，创建
        mkdir -p $WORKDIR
    fi

    # 执行DP测试
    if [ -f "/opt/factorytest/dp_uvc_compare.py" ]; then
        # 创建临时文件保存输出
        TEMP_OUTPUT="/tmp/dp_test_output.txt"
        
        # 运行两次测试：第一次预热（让ffplay渲染+UVC设备稳定），第二次才是真正结果
        for RUN in 1 2; do
            # 后台运行测试，40秒超时，禁用Python输出缓冲
            env XDG_RUNTIME_DIR=/root WAYLAND_DISPLAY=wayland-1 SDL_VIDEODRIVER=wayland \
                python3 -u /opt/factorytest/dp_uvc_compare.py --workdir $WORKDIR --threshold 0.90 > $TEMP_OUTPUT 2>&1 &

            DP_PID=$!

            # 等待最多40秒（实际测试约30秒完成，留一些容错空间）
            COUNT=0
            while [ $COUNT -lt 40 ]; do
                if ! kill -0 $DP_PID 2>/dev/null; then
                    # 进程已结束
                    break
                fi
                sleep 1
                COUNT=$((COUNT + 1))
            done

            # 等待进程完全结束，确保输出文件写完
            wait $DP_PID 2>/dev/null || true

            # 如果超时强制结束
            if [ $COUNT -eq 40 ]; then
                kill -9 $DP_PID 2>/dev/null
                test_event "dp:fail:timeout on run $RUN"
                break
            fi
            
            # 第一次运行作为预热，不检查结果
            if [ $RUN -eq 1 ]; then
                continue
            fi
            
            # 第二次运行才检查结果
            sync
            sleep 1
            
            # 检查输出中是否包含 "result: successful"
            if grep -q "result: successful" $TEMP_OUTPUT 2>/dev/null; then
                test_event "dp:pass"
            else
                test_event "dp:fail"
            fi
        done
        
        # 保留临时文件不清理，供调试使用
        # rm -f $TEMP_OUTPUT
    else
        test_event "dp:fail:dp_uvc_compare.py not found"
    fi
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
