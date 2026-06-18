# -*- coding: utf-8 -*-
"""检查 DeltaForce 相关进程"""
import psutil
import time
import sys

def find_delta_processes():
    print("=== DeltaForce 相关进程 ===\n")
    found = []
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            name = proc.info['name'] or ''
            exe = proc.info['exe'] or ''
            cmdline = ' '.join(proc.info['cmdline'] or [])

            if any(kw in name.lower() or kw in exe.lower() or kw in cmdline.lower()
                   for kw in ['delta', 'dfac', 'game', 'tencent', 'battle', 'tx', 'anticheat', 'sgx']):
                print(f"[{proc.info['pid']:>6}] {name}")
                print(f"       exe: {exe}")
                print(f"       cmd: {cmdline[:100]}")
                print()
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if not found:
        print("未找到 DeltaForce 相关进程\n")

    print("=== 所有游戏/可疑进程 ===\n")
    game_kws = ['game', 'client', 'engine', 'render', 'anticheat', 'sgx', 'tencent', 'battle', 'play', 'online']
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            name = proc.info['name'] or ''
            exe = proc.info['exe'] or ''
            if any(kw in name.lower() for kw in game_kws):
                print(f"[{proc.info['pid']:>6}] {name} | {exe}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

if __name__ == '__main__':
    find_delta_processes()