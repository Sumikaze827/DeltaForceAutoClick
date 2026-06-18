# -*- coding: utf-8 -*-
"""
三角洲行动典藏皮肤抢购工具

使用方法:
   & "venv/Scripts/python.exe" main.py           # 使用 venv 环境
   & "venv/Scripts/python.exe" -m PyInstaller main.spec
退出: 按 ESC 或关闭窗口
"""
import sys
import os
import time
import json
import threading
import sys
import os
import time
import json
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_kms_path = os.path.join(os.path.dirname(__file__), 'kms')
if os.path.isdir(_kms_path):
    sys.path.insert(0, _kms_path)

import mss
import numpy as np

# ============================================================
# 配置加载
# ============================================================
def load_config():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base, 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "delay": 860,
        "1920x1080": {
            "ZONE4": [1562, 874, 1725, 898],
            "ZONE1": [1638, 922, 1657, 943],
            "SUCCESS_REGION": [1646, 870, 1722, 885],
            "MOVE1_POS": [1639, 937],
            "MOVE2_POS": [1235, 706],
            "REFRESH_POS": [1378, 178],
            "BACK_POS": [940, 940],
        }
    }

def save_config(config):
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base, 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

CONFIG = load_config()
DELAY_MS = CONFIG.get('delay', 860)

ZONE4   = CONFIG.get('1920x1080', {}).get('ZONE4',   [1562, 874, 1725, 898])
ZONE1   = CONFIG.get('1920x1080', {}).get('ZONE1',   [1638, 922, 1657, 943])
SUCCESS = CONFIG.get('1920x1080', {}).get('SUCCESS_REGION', [1646, 870, 1722, 885])
MOVE1_POS = CONFIG.get('1920x1080', {}).get('MOVE1_POS', [1639, 937])
MOVE2_POS = CONFIG.get('1920x1080', {}).get('MOVE2_POS', [1235, 706])
REFRESH_POS = CONFIG.get('1920x1080', {}).get('REFRESH_POS', [1378, 178])
BACK_POS = CONFIG.get('1920x1080', {}).get('BACK_POS', [940, 940])
RESULT_ZONE = CONFIG.get('1920x1080', {}).get('RESULT_ZONE', [0, 0, 0, 0])

ZONE4_REGION   = (ZONE4[0], ZONE4[1], ZONE4[2] - ZONE4[0], ZONE4[3] - ZONE4[1])
ZONE1_REGION   = (ZONE1[0], ZONE1[1], ZONE1[2] - ZONE1[0], ZONE1[3] - ZONE1[1])
SUCCESS_REGION = (SUCCESS[0], SUCCESS[1], SUCCESS[2] - SUCCESS[0], SUCCESS[3] - SUCCESS[1])
RESULT_REGION = (RESULT_ZONE[0], RESULT_ZONE[1], RESULT_ZONE[2] - RESULT_ZONE[0], RESULT_ZONE[3] - RESULT_ZONE[1])
ENTER_POS     = (MOVE1_POS[0], MOVE1_POS[1])
CONFIRM_POS   = (MOVE2_POS[0], MOVE2_POS[1])
REFRESH_POS_T = (REFRESH_POS[0], REFRESH_POS[1])
BACK_POS_T    = (BACK_POS[0], BACK_POS[1])

# ============================================================
# OCR
# ============================================================
def create_ocr():
    try:
        import ddddocr
        ocr = ddddocr.DdddOcr(show_ad=False)
        print("[OCR] 使用 ddddocr (venv)")
        return ocr, 'ddddocr'
    except Exception:
        pass
    try:
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        print("[OCR] 使用 RapidOCR (venv)")
        return ocr, 'rapidocr'
    except Exception:
        pass
    return None, None

class OCRHandler:
    def __init__(self):
        self._ocr, self._mode = create_ocr()

    def recognize(self, image):
        start = time.time()
        if self._mode == 'ddddocr':
            import cv2
            if not isinstance(image, bytes):
                _, buf = cv2.imencode('.png', image)
                image = buf.tobytes()
            result = self._ocr.classification(image)
        elif self._mode == 'rapidocr':
            result, _ = self._ocr(image)
            if result:
                result = ' '.join([item[1] for item in result])
            else:
                result = None
        else:
            result = None
        self._last_duration = time.time() - start
        return result

    def extract_countdown(self, text):
        if not text:
            return None
        chinese_map = {'零':'0','一':'1','二':'2','三':'3','四':'4','五':'5','六':'6','七':'7','八':'8','九':'9',
                       '分':':', '秒':'', '：':':', '，':'', ',':'', '。':'', '.':''}
        for k, v in chinese_map.items():
            text = text.replace(k, v)
        import re
        # 匹配 MM:SS 或 M:SS 格式，转换为总秒数
        mmss_match = re.search(r'(\d{1,2}):(\d{1,2})', text)
        if mmss_match:
            minutes = int(mmss_match.group(1))
            seconds = int(mmss_match.group(2))
            if seconds < 60:
                return minutes * 60 + seconds
        # 回退：取最后一个合法数字（秒数 <= 59）
        digits = re.findall(r'\d+', text)
        if not digits:
            return None
        val = int(digits[-1])
        if val <= 59:
            return val
        return None

    def recognize_countdown(self, image):
        start = time.time()
        raw = self.recognize(image) or ""
        self._last_duration = time.time() - start
        digits = self.extract_countdown(raw)
        return digits, raw.strip()

    def get_last_duration_ms(self):
        return round(self._last_duration * 1000, 1)

# ============================================================
# 鼠标（Win32 API）
# ============================================================
import ctypes
from ctypes import wintypes
user32 = ctypes.windll.user32
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

def _set_cursor_pos(x, y):
    user32.SetCursorPos(int(x), int(y))

def mouse_click(x, y):
    _set_cursor_pos(x, y)
    time.sleep(0.005)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

def press_esc():
    user32.keybd_event(0x1B, 0, 0, 0)  # ESC down
    time.sleep(0.01)
    user32.keybd_event(0x1B, 0, 0x0002, 0)  # ESC up

# ============================================================
# KMS 反检测
# ============================================================
def init_kms(log_callback=None):
    try:
        from kms import init_anti_detect
        init_anti_detect(lambda: None)
        msg = "[KMS] 反检测已启用"
        if log_callback:
            log_callback(msg)
        else:
            print(msg)
    except Exception as e:
        msg = f"[KMS] 不可用: {e}"
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

# ============================================================
# 屏幕捕获
# ============================================================
class ScreenCapture:
    def __init__(self):
        self.sct = mss.MSS()

    def capture_to_numpy(self, region):
        x, y, w, h = region
        img = self.sct.grab({"left": int(x), "top": int(y), "width": int(w), "height": int(h)})
        return np.array(img)[..., :3]

    def close(self):
        self.sct.close()

# ============================================================
# 抢购逻辑
# ============================================================
class GrabRunner(threading.Thread):
    def __init__(self, ocr_handler, status_callback, log_callback, batch_mode=False, self_correct=False, self_correct_cb=None):
        super().__init__(daemon=True)
        self.running = False
        self.ocr = ocr_handler
        self.capture = ScreenCapture()
        self.status_callback = status_callback
        self.log_callback = log_callback
        self.last_digits = None
        self.state = "idle"
        self._refreshed = False
        self._idle_wait_counter = 0
        self._entering_elapsed = 0
        self._entering_has_countdown = False  # entering状态是否读到过有效倒计时
        self._countdown_last_refresh = 0  # countdown上次刷新时间戳
        self._batch_mode = batch_mode
        self._self_correct = self_correct
        self._self_correct_cb = self_correct_cb
        self._last_ocr_ms = 0
        self._log_dir = None
        self._log_file = None

    def _log(self, msg):
        self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _status(self, text, color="white"):
        self.status_callback(text, color)

    def _init_result_log(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        stamp = datetime.now().strftime('%Y%m%d')
        log_dir = os.path.join(base, 'result_logs')
        os.makedirs(log_dir, exist_ok=True)
        self._log_file = os.path.join(log_dir, f'{stamp}.log')

    def _write_result_log(self, category, ocr_ms, raw):
        self._log(f"[DEBUG] 写入日志: category={category}, file={self._log_file}")
        if not self._log_file:
            self._log("日志文件未初始化")
            return
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                ts = datetime.now().strftime('%H:%M:%S')
                f.write(f"[{ts}] [{category}] OCR:{ocr_ms}ms | {raw}\n")
                f.flush()
            self._log(f"日志写入成功")
        except Exception as e:
            self._log(f"日志写入失败: {e}")

    def _check_result(self):
        # 持续捕获直到识别到文字，保底3秒
        results = []
        start = time.time()
        first_capture_time = None
        while self.running:
            img = self.capture.capture_to_numpy(RESULT_REGION)
            r = self.ocr.recognize(img) or ""
            ocr_ms = self.ocr.get_last_duration_ms()
            results.append((r, ocr_ms))
            if first_capture_time is None:
                first_capture_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            if r:
                break
            if time.time() - start >= 3:
                break
            time.sleep(0.05)

        # 优先选非空且文字最多的结果
        best = max(results, key=lambda x: len(x[0]))
        raw, ocr_ms = best
        self._last_ocr_ms = ocr_ms

        all_raw = [r[0] for r in results]
        self._log(f"首次捕获@{first_capture_time} | {len(results)}次结果: {all_raw}")

        if "成功" in raw:
            self._log(f"✅ 购买成功! ({ocr_ms}ms)")
            self._status("成功", "green")
            self.click(*BACK_POS_T, "返回")
            return "success"
        elif "支付" in raw:
            self._log(f"💰 支付页面 ({ocr_ms}ms)")
            self._write_result_log("支付", ocr_ms, raw)
        elif "下架" in raw:
            self._log(f"⚠️ 下架 ({ocr_ms}ms)")
            self._write_result_log("下架", ocr_ms, raw)
            if self._self_correct and self._self_correct_cb:
                self._self_correct_cb(-1, "下架")
        elif "队列满" in raw or "队列已满" in raw:
            self._log(f"⚠️ 队列满 ({ocr_ms}ms)")
            self._write_result_log("队列满", ocr_ms, raw)
            if self._self_correct and self._self_correct_cb:
                self._self_correct_cb(-1, "队列满")
        elif "公示期" in raw or "尚未" in raw:
            self._log(f"⚠️ 公示期 ({ocr_ms}ms)")
            self._write_result_log("公示期", ocr_ms, raw)
            if self._self_correct and self._self_correct_cb:
                self._self_correct_cb(1, "公示期")
        else:
            self._log(f"结果未知: {raw} ({ocr_ms}ms)")
            self._write_result_log("未知", ocr_ms, raw)

        self.click(*BACK_POS_T, "返回")
        return "continue"

    def click(self, x, y, label):
        self._log(f"点击 {label} ({x}, {y})")
        mouse_click(x, y)

    def run(self):
        self.running = True
        self._log("抢购线程启动")
        self._status("空闲", "gray")
        self._jump_confirm_count = 0
        self._jump_value = None
        self._jump_confirming = False
        self._init_result_log()

        while self.running:
            try:
                img = self.capture.capture_to_numpy(ZONE4_REGION)
                digits, raw = self.ocr.recognize_countdown(img)

                if digits is not None and self.state not in {"entering", "done"}:
                    ocr_ms = self.ocr.get_last_duration_ms()
                    self._last_ocr_ms = ocr_ms
                    self._idle_wait_counter = 0

                    self._log(f"主倒计时: {digits}s | OCR {ocr_ms}ms | {self.state}")

                    # 批量模式：countdown状态每15秒点一次刷新
                    if self._batch_mode and self.state == "countdown":
                        now = time.time()
                        if self._countdown_last_refresh == 0:
                            self._countdown_last_refresh = now
                            self._log("批量模式：进入countdown，点击刷新")
                            self.click(*REFRESH_POS_T, "刷新")
                            time.sleep(0.5)
                        elif now - self._countdown_last_refresh >= 15:
                            elapsed = int(now - self._countdown_last_refresh)
                            self._countdown_last_refresh = now
                            self._log(f"批量模式：距上次刷新{elapsed}秒，点击刷新")
                            self.click(*REFRESH_POS_T, "刷新")
                            time.sleep(0.5)

                    if self._jump_confirming:
                        # 跳变确认中：比较当前帧与锚定值
                        if abs(digits - self._jump_value) >= 5:
                            # 帧间差值仍大，重置锚定值和计数
                            self._jump_value = digits
                            self._jump_confirm_count = 0
                            self._log(f"跳变重置: →{digits}，重新确认")
                        self._jump_confirm_count += 1
                        if self._jump_confirm_count >= 5:
                            self._log(f"跳变确认通过: {digits}s")
                            self.last_digits = digits
                            self._jump_confirming = False
                            self._jump_value = None
                            self._jump_confirm_count = 0
                        else:
                            self._log(f"跳变确认 {self._jump_confirm_count}/5: {digits}s")
                        time.sleep(0.05)
                        continue
                    elif self.last_digits is not None and abs(digits - self.last_digits) >= 5:
                        # 检测到跳变，开始确认流程
                        self._jump_value = digits
                        self._jump_confirm_count = 0
                        self._jump_confirming = True
                        self._log(f"跳变检测: {self.last_digits}→{digits}，开始确认")
                        time.sleep(0.05)
                        continue
                    else:
                        self._jump_value = None
                        self._jump_confirm_count = 0
                        self.last_digits = digits

                    if self.state == "idle" and digits > 0:
                        self.state = "countdown"
                        self._refreshed = False
                        self._countdown_last_refresh = 0  # 重置刷新计时
                    elif self.state == "countdown":
                        if not self._refreshed and digits <= 10:
                            self._log(f"倒计时 ≤ 10s，点击刷新")
                            self.click(*REFRESH_POS_T, "刷新")
                            self._refreshed = True
                            time.sleep(0.5)
                            continue
                        if digits <= 3:
                            self._log(f"倒计时 ≤ 3s，点击进入")
                            self.click(*ENTER_POS, "进入")
                            self.state = "entering"
                            self._status("进入中", "yellow")
                            self._entering_elapsed = 0
                            self._entering_has_countdown = False  # 重置倒计时标志
                            self._countdown_last_refresh = 0  # 重置刷新计时
                            self.last_digits = None  # 重置跳变检测，避免误判
                            time.sleep(0.5)
                            # 不 continue，让下一帧进 entering 读 ZONE1

                elif self.state in {"idle", "countdown"}:
                    # digits is None 时，batch模式也执行刷新逻辑
                    if self._batch_mode and self.state == "countdown":
                        now = time.time()
                        if self._countdown_last_refresh == 0:
                            self._countdown_last_refresh = now
                            self._log("批量模式：进入countdown，点击刷新")
                            self.click(*REFRESH_POS_T, "刷新")
                            time.sleep(0.5)
                        elif now - self._countdown_last_refresh >= 15:
                            elapsed = int(now - self._countdown_last_refresh)
                            self._countdown_last_refresh = now
                            self._log(f"批量模式：距上次刷新{elapsed}秒，点击刷新")
                            self.click(*REFRESH_POS_T, "刷新")
                            time.sleep(0.5)
                    time.sleep(0.05)
                    continue

                elif self.state == "entering":
                    self._entering_elapsed += 1
                    if self._entering_elapsed == 1:
                        self._log("等待确认界面加载...")
                        time.sleep(0.5)
                    img2 = self.capture.capture_to_numpy(ZONE1_REGION)
                    cdigits, raw = self.ocr.recognize_countdown(img2)
                    ocr_ms = self.ocr.get_last_duration_ms()
                    self._log(f"ZONE1: {cdigits}s raw='{raw}' | OCR {ocr_ms}ms")
                    self._last_ocr_ms = ocr_ms
                    if cdigits is not None and cdigits == 0:
                        adjusted_delay = max(0, DELAY_MS - self._last_ocr_ms)
                        self._log(f"确认归零，等待 {adjusted_delay}ms (原始{DELAY_MS}ms - OCR{self._last_ocr_ms}ms)")
                        time.sleep(adjusted_delay / 1000)
                        self.click(*CONFIRM_POS, "确认")
                        self.state = "done"
                        time.sleep(0.3)
                    elif cdigits is not None:
                        self._entering_has_countdown = True
                    elif cdigits is None:
                        if self._entering_elapsed > 5 and not self._entering_has_countdown:
                            self._log("ZONE1 持续无内容，返回countdown")
                            self.click(*BACK_POS_T, "返回")
                            self.state = "countdown"
                            self._entering_elapsed = 0
                            self._countdown_last_refresh = 0
                            time.sleep(0.3)
                        elif self._entering_elapsed > 40:
                            self._log(f"ZONE1 超时，返回countdown")
                            self.click(*BACK_POS_T, "返回")
                            self.state = "countdown"
                            self._entering_elapsed = 0
                            self._countdown_last_refresh = 0
                            time.sleep(0.3)
                        else:
                            self._log("ZONE1 无内容，等待...")
                            time.sleep(0.05)

                elif self.state == "done":
                    result = self._check_result()
                    if result == "success":
                        pass  # 已停止
                    # 重置状态，继续监控
                    self.state = "idle"
                    self.last_digits = None
                    self._refreshed = False
                    self._countdown_last_refresh = 0
                    self._countdown_elapsed = 0
                    continue

                else:
                    if self.state == "idle":
                        self._idle_wait_counter += 1
                        if self._idle_wait_counter % 20 == 0:
                            self._log("等待主界面倒计时...")

                time.sleep(0.05)

            except Exception as e:
                self._log(f"异常: {e}")
                time.sleep(1)

        self.capture.close()
        self._log("抢购线程结束")
        self._status("已停止", "red")

    def stop(self):
        self.running = False


# ============================================================
# GUI
# ============================================================
def start_gui():
    import tkinter as tk
    from tkinter import scrolledtext

    root = tk.Tk()
    root.title("DFAC")
    root.geometry("600x480")
    root.attributes('-topmost', 1)

    # 状态标签
    status_label = tk.Label(root, text="空闲", font=('Consolas', 24, 'bold'),
                            fg='gray', bg='#1e1e1e', width=20, height=2)
    status_label.pack(pady=8)

    # 控制按钮区 + 置顶选项
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=5)

    topmost_var = tk.BooleanVar(value=True)

    def force_topmost():
        if topmost_var.get():
            hwnd = root.winfo_id()
            user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0004)
            root.after(100, force_topmost)

    def on_topmost_toggle():
        if topmost_var.get():
            force_topmost()
        else:
            hwnd = root.winfo_id()
            user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0004)

    cb_topmost = tk.Checkbutton(btn_frame, text="置顶", variable=topmost_var,
                                command=on_topmost_toggle, font=('Consolas', 10))
    cb_topmost.pack(side=tk.LEFT, padx=5)

    batch_mode_var = tk.BooleanVar(value=CONFIG.get('batch_mode', False))
    cb_batch = tk.Checkbutton(btn_frame, text="批量模式", variable=batch_mode_var,
                              font=('Consolas', 10))
    cb_batch.pack(side=tk.LEFT, padx=5)

    self_correct_var = tk.BooleanVar(value=CONFIG.get('self_correct', False))
    cb_self_correct = tk.Checkbutton(btn_frame, text="自修正", variable=self_correct_var,
                                    font=('Consolas', 10))
    cb_self_correct.pack(side=tk.LEFT, padx=5)

    def save_bool_config(key, value):
        config = load_config()
        config[key] = value
        save_config(config)

    batch_mode_var.trace_add('write', lambda *_: save_bool_config('batch_mode', batch_mode_var.get()))
    self_correct_var.trace_add('write', lambda *_: save_bool_config('self_correct', self_correct_var.get()))

    if topmost_var.get():
        root.after(200, force_topmost)

    # 延迟设置区
    delay_frame = tk.Frame(root)
    delay_frame.pack(pady=5)
    tk.Label(delay_frame, text="延迟(ms):", font=('Consolas', 11)).pack(side=tk.LEFT)

    delay_var = tk.IntVar(value=DELAY_MS)
    delay_entry = tk.Entry(delay_frame, textvariable=delay_var, font=('Consolas', 11), width=7)
    delay_entry.pack(side=tk.LEFT, padx=5)

    def adjust_delay(delta):
        delay_var.set(max(0, delay_var.get() + delta))
        on_delay_change()

    tk.Button(delay_frame, text="-1", font=('Consolas', 10), width=3,
              command=lambda: adjust_delay(-1)).pack(side=tk.LEFT, padx=2)
    tk.Button(delay_frame, text="+1", font=('Consolas', 10), width=3,
              command=lambda: adjust_delay(1)).pack(side=tk.LEFT, padx=2)

    def on_delay_change(*_):
        global DELAY_MS
        try:
            DELAY_MS = max(0, int(delay_entry.get()))
            # 保存到 config.json
            config = load_config()
            config['delay'] = DELAY_MS
            save_config(config)
        except ValueError:
            pass

    delay_entry.bind('<KeyRelease>', on_delay_change)

    # 启动/停止按钮
    runner_ref = [None]

    def set_status(text, color):
        status_label.config(text=text, fg=color)

    def add_log(msg):
        log_area.insert(tk.END, msg + "\n")
        log_area.see(tk.END)

    def on_self_correct(delta, keyword):
        new_val = delay_var.get() + delta
        delay_var.set(new_val)
        on_delay_change()
        add_log(f"[自修正] {keyword}，延迟{'+' if delta > 0 else ''}{delta}ms → {new_val}ms")

    def toggle():
        if runner_ref[0] is None or not runner_ref[0].running:
            ocr_h = OCRHandler()
            if ocr_h._mode is None:
                add_log("[错误] 未找到可用 OCR")
                return
            runner = GrabRunner(ocr_h, set_status, add_log, batch_mode_var.get(), self_correct_var.get(), on_self_correct)
            runner.start()
            runner_ref[0] = runner
            btn_start.config(state='disabled')
            btn_stop.config(state='normal')
            mode_str = " (批量模式)" if batch_mode_var.get() else ""
            add_log(f"抢购已启动{mode_str}")
        else:
            runner_ref[0].stop()
            btn_start.config(state='normal')
            btn_stop.config(state='disabled')

    btn_start = tk.Button(btn_frame, text="启动", font=('Consolas', 14),
                          command=toggle, width=8, bg="#2d5")
    btn_stop = tk.Button(btn_frame, text="停止", font=('Consolas', 14),
                         command=toggle, width=8, bg="#d52", state='disabled')
    btn_start.pack(side=tk.LEFT, padx=5)
    btn_stop.pack(side=tk.LEFT, padx=5)

    # 日志区
    tk.Button(root, text="清空日志", font=('Consolas', 10),
             command=lambda: log_area.delete('1.0', tk.END)).pack(pady=2)
    log_area = scrolledtext.ScrolledText(root, font=('Consolas', 10),
                                          height=20, bg='#1e1e1e', fg='#0f0')
    log_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

    init_kms(add_log)

    def on_esc(e):
        if runner_ref[0]:
            runner_ref[0].stop()
        root.destroy()

    root.bind('<Escape>', on_esc)
    root.protocol("WM_DELETE_WINDOW", lambda: on_esc(None))

    root.mainloop()


def main():
    start_gui()

if __name__ == "__main__":
    main()