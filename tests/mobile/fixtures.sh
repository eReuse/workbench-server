#!/usr/bin/env bash
echo 'This requires "adb" installed.'
echo 'If it says "no devices/emulators... it means that the Android:'
echo '- Is not plugged in or it had a micro cut. Check cable and try again.'
echo '- You have not given access to adb. Check https://developer.android.com/studio/command-line/adb#Enabling'
echo '"Cant find service" errors are ok.'
echo ''
m=$(adb shell getprop ro.product.model)
# trim From https://stackoverflow.com/a/3232433/2710757
model=$(echo -e "${m}" | tr -d '[:space:]')
mkdir -p files
echo "Generating files for $model in a folder called 'files'..."
adb shell getprop > "files/getprop.$model.txt"
adb shell dumpsys > "files/dumpsys.$model.txt"
adb shell dumpsys meminfo -c > "files/meminfo.dumpsys.$model.txt"
adb shell cat /proc/meminfo > "files/meminfo.$model.txt"
adb shell dumpsys battery > "files/battery.dumpsys.$model.txt"
adb shell dumpsys batterymanager > "files/batterymanager.dumpsys.$model.txt"
adb shell ls /sys/devices/system/cpu > "files/cpu-ls.$model.txt"
adb shell ip addr show > "files/ip.$model.txt"
adb shell settings get secure bluetooth_address > "files/bluetooth_address.$model.txt"
adb shell cat /proc/cpuinfo > "files/cpuinfo.$model.txt"
adb shell service call iphonesubinfo 1 > "files/iphonesubinfo.1.$model.txt"
adb shell service call iphonesubinfo 16 > "files/iphonesubinfo.16.$model.txt"
adb shell df -h /data > "files/data.df.$model.txt"
adb shell df -h /system > "files/system.df.$model.txt"
echo "Done. Files are in 'files' directory."
