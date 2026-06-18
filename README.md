# DFAC - 三角洲行动典藏皮肤抢购工具

一个基于 OCR 视觉识别的三角洲行动典藏皮肤自动抢购工具。自动检测倒计时，在最佳时机自动点击抢购。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-blue.svg)

## 功能特性

- **OCR 倒计时检测** - 支持 `ddddocr` / `RapidOCR` 双引擎，自动识别游戏倒计时
- **零延迟点击** - 根据 OCR 耗时动态补偿，确保精确到毫秒级触发
- **跳变检测与确认** - 检测倒计时异常跳变（网络/显示延迟），5帧确认机制避免误触
- **批量模式** - 支持连续监控，每15秒自动刷新页面
- **自纠错机制** - 遇"公示期"/"队列满"/"下架"等状态自动调整策略
- **KMS 反检测** - 内置隐藏反检测模块（需要 `kms/` 目录支持）
- **结果日志** - 每次操作结果实时记录到 `result_logs/`

## 目录结构

```
DFAC/
├── main.py              # 主程序入口
├── main.spec            # PyInstaller 打包配置
├── config.json          # 屏幕坐标与参数配置
├── check_process.py     # 进程检查脚本
├── kms/                 # KMS 反检测模块（可选）
├── result_logs/         # 操作日志输出目录
├── build/               # 打包临时文件
└── dist/                # 打包输出目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `ddddocr` 或 `rapidocr_onnxruntime`（OCR 识别）
- `mss`（屏幕截图）
- `numpy`（图像处理）
- `opencv-python`（图像编码）
- `Pillow`（图像处理）

### 2. 配置

编辑 `config.json`，根据你的屏幕分辨率设置各区域坐标：

| 配置项 | 说明 |
|--------|------|
| `delay` | 抢购触发延迟（毫秒） |
| `ZONE4` | 主倒计时检测区域 `[x1, y1, x2, y2]` |
| `ZONE1` | 确认倒计时检测区域 |
| `SUCCESS_REGION` | 成功标识检测区域 |
| `MOVE1_POS` | "进入"按钮坐标 |
| `MOVE2_POS` | "确认"按钮坐标 |
| `REFRESH_POS` | "刷新"按钮坐标 |
| `BACK_POS` | "返回"按钮坐标 |

### 3. 运行

**开发模式：**
```bash
python main.py
```

**打包为 EXE：**
```bash
pyinstaller main.spec
```

打包后 EXE 位于 `dist/DFAC.exe`。

### 4. 使用方法

1. 运行程序，进入游戏皮肤购买页面
2. 确保倒计时区域在屏幕可视范围内
3. 点击窗口或按 `F1` 开始监控（或根据 UI 按钮操作）
4. 程序将自动：
   - 监控主倒计时（ZONE4）
   - 检测倒计时 ≤ 3s 时点击"进入"
   - 监控确认倒计时（ZONE1）
   - 倒计时归零时精确点击"确认"
   - 检测并记录购买结果
5. 按 `ESC` 或关闭窗口退出

## 核心逻辑

```
idle → countdown → entering → done → (idle)
         ↑           ↓
         └───────────┘
```

1. **idle** - 等待主界面倒计时出现
2. **countdown** - 监控倒计时，≤10s 刷新页面，≤3s 点击进入
3. **entering** - 监控二次确认倒计时，归零时精确触发
4. **done** - 检测结果（成功/支付/下架/队列满），返回 idle 继续

## 注意事项

- 本工具仅供学习研究，请勿用于商业用途或违规操作
- 使用前请确保游戏和网络环境稳定
- 目前只支持1k分辨率
- 部分功能需要 `kms/` 模块支持

## License

MIT License
