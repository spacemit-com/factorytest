#!/bin/bash

test_size=1G
test_loop=1

while true
do
    memtester $test_size $test_loop
    [ $? -eq 0 ] || exit -1
done