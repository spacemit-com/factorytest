#!/bin/bash -e

for gpio in "$@"
do
    echo $gpio > /sys/class/gpio/export
    echo out > /sys/class/gpio/gpio$gpio/direction
done

while true
do
    for gpio in "$@"
    do
        echo 1 > /sys/class/gpio/gpio$gpio/value
    done
    sleep 0.5

    for gpio in "$@"
    do
        echo 0 > /sys/class/gpio/gpio$gpio/value
    done
    sleep 0.5
done
