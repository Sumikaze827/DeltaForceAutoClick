# kms - 反检测模块
from .anti_detect import (
    check_debugger,
    check_remote_debugger,
    apply_stealth_window,
    maintain_stealth_window,
    protect_process,
    randomize_memory_layout,
    start_guardian_thread,
    init_anti_detect,
    get_fake_title,
)

__all__ = [
    'check_debugger',
    'check_remote_debugger',
    'apply_stealth_window',
    'maintain_stealth_window',
    'protect_process',
    'randomize_memory_layout',
    'start_guardian_thread',
    'init_anti_detect',
    'get_fake_title',
]