# -*- coding: utf-8 -*-
"""
反检测模块 - 编译为 .pyd 后由主程序导入
包含：反调试、窗口隐身、进程保护、反内存扫描、守护线程
使用 Cython 编译：python setup.py build_ext --inplace
"""
import ctypes
import ctypes.wintypes
import os
import random
import threading
import time

# ==================== 常量定义 ====================
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
WS_EX_NOACTIVATE = 0x08000000

ProcessDebugPort = 7
ProcessDebugObjectHandle = 30
ProcessDebugFlags = 31

_FAKE_TITLES = [
    "Windows 资源管理器", "系统进程服务", "Microsoft Windows 更新助手",
    "系统后台服务", "Windows 服务主机", "设备管理器服务",
    "Windows 系统进程", "系统维护服务", "Windows 搜索索引", "系统后台进程",
    "系统通知服务", "剪贴板用户服务", "输入法宿主进程", "Windows 网络服务",
    "系统时间服务", "磁盘整理程序", "Windows 音频服务进程", "系统辅助服务",
    "WUDFHost", "sihost", "taskeng", "MusNotifyIcon",
    "SecurityHealthService", "WLANExt", "WerFault",
]


def check_debugger():
    """检测本地调试器（IsDebuggerPresent）"""
    try:
        return bool(ctypes.windll.kernel32.IsDebuggerPresent())
    except Exception:
        return False


def check_remote_debugger():
    """检测远程调试器（NtQueryInformationProcess）"""
    try:
        ntdll = ctypes.windll.ntdll
        k32 = ctypes.windll.kernel32
        # 设置正确的函数签名（64位系统上HANDLE是8字节，必须设argtypes否则被截断为4字节）
        ntdll.NtQueryInformationProcess.argtypes = [
            ctypes.wintypes.HANDLE, ctypes.c_ulong,
            ctypes.c_void_p, ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong)
        ]
        ntdll.NtQueryInformationProcess.restype = ctypes.c_long
        hProc = k32.GetCurrentProcess()
        # ProcessDebugPort (7)
        debug_port = ctypes.c_size_t(0)
        status = ntdll.NtQueryInformationProcess(hProc, ProcessDebugPort, ctypes.byref(debug_port), ctypes.sizeof(debug_port), None)
        if status == 0 and debug_port.value != 0:
            return True
        # ProcessDebugObjectHandle (30)
        debug_object = ctypes.c_size_t(0)
        status2 = ntdll.NtQueryInformationProcess(hProc, ProcessDebugObjectHandle, ctypes.byref(debug_object), ctypes.sizeof(debug_object), None)
        if status2 == 0 and debug_object.value != 0:
            return True
        return False
    except Exception:
        return False


def _hide_from_taskbar(hwnd):
    """使用 ITaskbarList 接口从任务栏隐藏窗口（不影响标题栏外观）"""
    try:
        user32 = ctypes.windll.user32
        real_hwnd = user32.GetParent(hwnd) or hwnd
        # 定义 ITaskbarList 接口 GUID
        CLSID_TaskList = ctypes.GUID('{56FDF344-FD6D-11d0-958A-006097C9A090}')
        IID_ITaskbarList = ctypes.GUID('{56FDF342-FD6D-11d0-958A-006097C9A090}')
        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)
        try:
            p_taskbar = ctypes.POINTER(ctypes.c_void_p)()
            ole32.CoCreateInstance(
                ctypes.byref(CLSID_TaskList), None, 1,
                ctypes.byref(IID_ITaskbarList), ctypes.byref(p_taskbar)
            )
            if p_taskbar and p_taskbar.value:
                # ITaskbarList::DeleteTab(hwnd) — vtable 第3个方法（索引2）
                vtable = ctypes.cast(p_taskbar.value, ctypes.POINTER(ctypes.c_void_p))
                delete_tab_fn = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)(vtable[2])
                delete_tab_fn(p_taskbar.value, real_hwnd)
        finally:
            ole32.CoUninitialize()
    except Exception:
        pass


def apply_stealth_window(hwnd):
    """设置窗口隐身：去除 APPWINDOW 隐式隐藏任务栏 + NOACTIVATE，保持正常标题栏和最小化功能"""
    try:
        user32 = ctypes.windll.user32
        real_hwnd = user32.GetParent(hwnd) or hwnd
        # 去掉 APPWINDOW（隐式不在任务栏显示），加 NOACTIVATE（不自动抢焦点）
        # 不设 WS_EX_TOOLWINDOW（避免标题栏变窄）
        # 不调用 DeleteTab（避免破坏最小化到任务栏的功能）
        ex_style = user32.GetWindowLongPtrW(real_hwnd, GWL_EXSTYLE)
        ex_style = (ex_style & ~WS_EX_APPWINDOW) | WS_EX_NOACTIVATE
        # 确保 TOOLWINDOW 被清除（恢复完整标题栏）
        ex_style &= ~WS_EX_TOOLWINDOW
        user32.SetWindowLongPtrW(real_hwnd, GWL_EXSTYLE, ex_style)
    except Exception:
        pass


def maintain_stealth_window(hwnd):
    """持续保持窗口隐身属性（防止被重置），不影响最小化功能"""
    try:
        user32 = ctypes.windll.user32
        real_hwnd = user32.GetParent(hwnd) or hwnd
        ex_style = user32.GetWindowLongPtrW(real_hwnd, GWL_EXSTYLE)
        changed = False
        # 确保 NOACTIVATE
        if not (ex_style & WS_EX_NOACTIVATE):
            ex_style |= WS_EX_NOACTIVATE
            changed = True
        # 确保没有 APPWINDOW（避免任务栏重新出现）
        if ex_style & WS_EX_APPWINDOW:
            ex_style &= ~WS_EX_APPWINDOW
            changed = True
        # 确保没有 TOOLWINDOW（恢复完整标题栏和正常最小化）
        if ex_style & WS_EX_TOOLWINDOW:
            ex_style &= ~WS_EX_TOOLWINDOW
            changed = True
        if changed:
            user32.SetWindowLongPtrW(real_hwnd, GWL_EXSTYLE, ex_style)
    except Exception:
        pass


def protect_process():
    """启用进程保护策略（DEP + 强制ASLR + 严格句柄检查）"""
    try:
        kernel32 = ctypes.windll.kernel32
        PROCESS_DEP_ENABLE = 0x00000001
        PROCESS_DEP_DISABLE_ATL_THUNK_EMULATION = 0x00000002
        kernel32.SetProcessDEPPolicy(PROCESS_DEP_ENABLE | PROCESS_DEP_DISABLE_ATL_THUNK_EMULATION)
    except Exception:
        pass
    try:
        kernel32 = ctypes.windll.kernel32
        class PROCESS_MITIGATION_ASLR_POLICY(ctypes.Structure):
            _fields_ = [
                ("EnableBottomUpRandomization", ctypes.c_ulong, 1),
                ("ForceRelocateImages", ctypes.c_ulong, 1),
                ("HighEntropy", ctypes.c_ulong, 1),
                ("DisallowStrippedImages", ctypes.c_ulong, 1),
                ("ReservedFlags", ctypes.c_ulong, 28),
            ]
        aslr_policy = PROCESS_MITIGATION_ASLR_POLICY()
        aslr_policy.EnableBottomUpRandomization = 1
        aslr_policy.ForceRelocateImages = 1
        aslr_policy.HighEntropy = 1
        try:
            kernel32.SetProcessMitigationPolicy(2, ctypes.byref(aslr_policy), ctypes.sizeof(aslr_policy))
        except Exception:
            pass
        class PROCESS_MITIGATION_STRICT_HANDLE_CHECK_POLICY(ctypes.Structure):
            _fields_ = [
                ("RaiseExceptionOnInvalidHandleReference", ctypes.c_ulong, 1),
                ("HandleExceptionsPermanentlyEnabled", ctypes.c_ulong, 1),
                ("ReservedFlags", ctypes.c_ulong, 30),
            ]
        handle_policy = PROCESS_MITIGATION_STRICT_HANDLE_CHECK_POLICY()
        handle_policy.RaiseExceptionOnInvalidHandleReference = 1
        handle_policy.HandleExceptionsPermanentlyEnabled = 1
        try:
            kernel32.SetProcessMitigationPolicy(4, ctypes.byref(handle_policy), ctypes.sizeof(handle_policy))
        except Exception:
            pass
    except Exception:
        pass


def anti_process_lock():
    """反进程锁定：设置进程缓解策略，防止游戏锁定"""
    protect_process()


def randomize_memory_layout():
    """随机内存分配干扰内存扫描"""
    try:
        import random as _rand
        kernel32 = ctypes.windll.kernel32
        for _ in range(3):
            size = _rand.randint(4096, 65536)
            kernel32.VirtualAlloc(None, size, 0x3000, 0x04)
    except Exception:
        pass


def get_fake_title():
    """返回随机伪装窗口标题"""
    return random.choice(_FAKE_TITLES)


_guardian_running = False


def _guardian_loop(get_root_callback):
    """后台守护线程：每5秒检测调试器 + 保持窗口隐身"""
    global _guardian_running
    _guardian_running = True
    while _guardian_running:
        try:
            time.sleep(5)
            _dbg = check_debugger()
            _rdbg = check_remote_debugger()
            if _dbg or _rdbg:
                ctypes.windll.kernel32.ExitProcess(0)
                return
            try:
                root = get_root_callback()
                if root:
                    try:
                        hwnd = root.winfo_id()
                        if hwnd:
                            maintain_stealth_window(hwnd)
                    except Exception:
                        pass
            except Exception:
                pass
            randomize_memory_layout()
        except Exception:
            pass


def start_guardian_thread(get_root_callback):
    """启动守护线程"""
    global _guardian_running
    if not _guardian_running:
        t = threading.Thread(target=_guardian_loop, args=(get_root_callback,), daemon=True)
        t.start()


def init_anti_detect(get_root_callback):
    """一键初始化全部反检测功能"""
    protect_process()
    anti_process_lock()
    randomize_memory_layout()
    try:
        root = get_root_callback()
        if root:
            try:
                hwnd = root.winfo_id()
                if hwnd:
                    apply_stealth_window(hwnd)
            except Exception:
                pass
    except Exception:
        pass
    start_guardian_thread(get_root_callback)
