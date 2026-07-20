#!/bin/bash -e

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
