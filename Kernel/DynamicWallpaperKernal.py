"""动态壁纸内核

提供两种动态壁纸策略：
1. 桌面内嵌播放（仅 Windows）：通过 WorkerW 技术把播放窗口嵌到桌面图标下方循环播放视频/动图。
2. 逐帧轮播（跨平台降级）：把视频/动图抽成帧，按设定帧率循环切换系统壁纸。

作者：壁纸生成器 NEXT
"""
from __future__ import annotations

import ctypes
import glob
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from typing import Callable, List, Optional

from PySide6.QtCore import (QObject, Qt, QThread, QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy, QWidget
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtMultimediaWidgets import QVideoWidget

from Kernel.Logger import logger

try:
    from PIL import Image, ImageSequence
except ImportError:  # pragma: no cover
    Image = None
    ImageSequence = None

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv", ".m4v", ".flv", ".mpeg", ".mpg", ".ts"}
ANIMATED_IMAGE_EXTENSIONS = {".gif", ".webp", ".png", ".apng"}

MEDIA_KIND_VIDEO = "video"
MEDIA_KIND_ANIMATED_IMAGE = "animated_image"
MEDIA_KIND_UNSUPPORTED = "unsupported"

MODE_AUTO = "auto"
MODE_EMBED = "embed"
MODE_FRAME = "frame"

MAX_FRAME_COUNT = 150          # 逐帧模式最多抽取的帧数
DEFAULT_FPS = 5                # 默认轮播帧率
MIN_FPS = 1
MAX_FPS = 15

# ---------------------------------------------------------------------------
# 媒体类型检测
# ---------------------------------------------------------------------------

def detect_media_kind(path: str) -> str:
    """检测本地文件属于视频、动图还是不支持的类型。"""
    if not path or not os.path.isfile(path):
        return MEDIA_KIND_UNSUPPORTED

    ext = os.path.splitext(path)[1].lower()

    if ext in VIDEO_EXTENSIONS:
        return MEDIA_KIND_VIDEO

    if ext in ANIMATED_IMAGE_EXTENSIONS:
        # 需要确认确实是动图（单帧按静态图处理）
        if Image is None:
            return MEDIA_KIND_UNSUPPORTED if ext == ".gif" else MEDIA_KIND_UNSUPPORTED
        try:
            with Image.open(path) as img:
                img.seek(1)
                return MEDIA_KIND_ANIMATED_IMAGE
        except EOFError:
            return MEDIA_KIND_UNSUPPORTED  # 静态图
        except Exception:
            # 解析失败时按扩展名宽松处理 GIF
            return MEDIA_KIND_ANIMATED_IMAGE if ext == ".gif" else MEDIA_KIND_UNSUPPORTED

    return MEDIA_KIND_UNSUPPORTED


def is_supported_media(path: str) -> bool:
    return detect_media_kind(path) != MEDIA_KIND_UNSUPPORTED


# ---------------------------------------------------------------------------
# 壁纸帧设置（轻量：不弹 UI，不依赖 Set_Wallpaper.exe 的主题参数）
# ---------------------------------------------------------------------------

def set_wallpaper_frame(path: str) -> None:
    """把一张静态图片设置为系统壁纸（供逐帧轮播内部使用）。"""
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    system = platform.system()
    if system == "Windows":
        _set_wallpaper_windows(path)
    elif system == "Linux":
        _set_wallpaper_linux(path)
    elif system == "Darwin":
        _set_wallpaper_darwin(path)
    else:
        raise NotImplementedError(f"暂不支持的系统: {system}")


def _set_wallpaper_windows(path: str) -> None:
    SPI_SETDESKWALLPAPER = 0x0014
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDWININICHANGE = 0x02
    ok = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, path, SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE
    )
    if not ok:
        raise RuntimeError("SystemParametersInfoW 设置壁纸失败")


def _set_wallpaper_linux(path: str) -> None:
    """尽力适配常见桌面环境；与 MainKernal.SetBackground 保持一致的思路。"""
    from urllib.parse import quote

    desktop_env = os.getenv("XDG_CURRENT_DESKTOP", "").lower()
    file_uri = f"file://{path}"
    commands = []

    if "gnome" in desktop_env or "ubuntu" in desktop_env or "unity" in desktop_env:
        commands = [["gsettings", "set", "org.gnome.desktop.background", "picture-uri", file_uri],
                    ["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", file_uri]]
    elif "mate" in desktop_env:
        commands = [["gsettings", "set", "org.mate.background", "picture-filename", path]]
    elif "cinnamon" in desktop_env:
        commands = [["gsettings", "set", "org.cinnamon.desktop.background", "picture-uri", file_uri]]
    elif "deepin" in desktop_env or "dde" in desktop_env:
        commands = [["dde-shell", "-c", "appearance", "--", "set", "-b", "background", path]]
    elif "xfce" in desktop_env:
        commands = [["xfconf-query", "-c", "xfce4-desktop", "-p",
                     "/backdrop/screen0/monitor0/image-path", "-s", path]]
    elif "kde" in desktop_env or "plasma" in desktop_env:
        # KDE 通过 dbus 脚本设置（与主程序一致）
        try:
            import dbus
            bus = dbus.SessionBus()
            plasma = bus.get_object("org.kde.plasmashell", "/PlasmaShell")
            plasma = dbus.Interface(plasma, dbus_interface="org.kde.PlasmaShell")
            enew_wall = quote(path, safe="")
            script = """
            var Desktops = desktops();
            for (i=0; i<Desktops.length; i++) {
                d = Desktops[i];
                d.wallpaperPlugin = "org.kde.image";
                d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
                d.writeConfig("Image", "file://%s")
            }
            """ % enew_wall
            plasma.evaluateScript(script)
            return
        except Exception:
            raise
    else:
        # 未知环境：尝试 GNOME 兼容路径
        commands = [["gsettings", "set", "org.gnome.desktop.background", "picture-uri", file_uri]]

    last_error = None
    for cmd in commands:
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=5)
            return
        except Exception as e:  # noqa: BLE001
            last_error = e
            continue
    if last_error:
        raise last_error
    raise RuntimeError("无法设置壁纸：未识别的桌面环境")


def _set_wallpaper_darwin(path: str) -> None:
    script = f'''
    tell application "System Events"
        tell every desktop
            set picture to "{path}"
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=5)


# ---------------------------------------------------------------------------
# 帧抽取
# ---------------------------------------------------------------------------

class FrameExtractionWorker(QThread):
    """后台线程：从 GIF/动图或视频中抽取壁纸帧。"""

    progress = Signal(int, int)          # current, total
    finished_ok = Signal(list)           # 帧文件路径列表
    failed = Signal(str)

    def __init__(self, media_path: str, out_dir: str, kind: str,
                 max_frames: int = MAX_FRAME_COUNT, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.media_path = media_path
        self.out_dir = out_dir
        self.kind = kind
        self.max_frames = max_frames
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            os.makedirs(self.out_dir, exist_ok=True)
            # 清理旧帧
            for old in glob.glob(os.path.join(self.out_dir, "frame_*.jpg")) + \
                       glob.glob(os.path.join(self.out_dir, "frame_*.png")):
                try:
                    os.remove(old)
                except OSError:
                    pass

            if self.kind == MEDIA_KIND_ANIMATED_IMAGE:
                frames = self._extract_from_image()
            else:
                frames = self._extract_from_video()

            if self._cancelled:
                self.failed.emit("已取消")
                return
            if not frames:
                self.failed.emit("未能从媒体文件中抽取到任何帧")
                return
            self.finished_ok.emit(frames)
        except _NeedQtExtraction:
            # 视频且 ffmpeg 不可用：由引擎在主线程降级到 QVideoSink 抽帧
            self.failed.emit(NEED_QT_EXTRACTION_TOKEN)
        except Exception as e:  # noqa: BLE001
            logger.error(f"抽帧失败: {e}")
            logger.debug(traceback.format_exc())
            self.failed.emit(str(e))

    # -- GIF / APNG / 动态 WebP -------------------------------------------------
    def _extract_from_image(self) -> List[str]:
        if Image is None:
            raise RuntimeError("未安装 Pillow，无法解析动图")

        frames: List[str] = []
        with Image.open(self.media_path) as img:
            total = getattr(img, "n_frames", 1)
            step = max(1, total // self.max_frames)
            # 计算采样后的目标帧数
            sampled_indices = list(range(0, total, step))[:self.max_frames]
            for i, index in enumerate(sampled_indices):
                if self._cancelled:
                    break
                img.seek(index)
                frame = img.convert("RGBA")
                # 合成到黑色背景（壁纸不支持透明）
                background = Image.new("RGBA", frame.size, (0, 0, 0, 255))
                background.alpha_composite(frame)
                out_path = os.path.join(self.out_dir, f"frame_{i:04d}.jpg")
                background.convert("RGB").save(out_path, "JPEG", quality=90)
                frames.append(out_path)
                self.progress.emit(i + 1, len(sampled_indices))
        return frames

    # -- 视频：优先 ffmpeg，其次 Qt 解码 ----------------------------------------
    def _extract_from_video(self) -> List[str]:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise _NeedQtExtraction()
        frames = _extract_video_ffmpeg(
            self.media_path, self.out_dir, self.max_frames,
            progress=lambda c, t: self.progress.emit(c, t),
            cancelled=lambda: self._cancelled,
        )
        if frames is None:
            raise _NeedQtExtraction()
        return frames


class _NeedQtExtraction(Exception):
    """内部信号：需要在主线程用 QVideoSink 继续抽帧。"""


NEED_QT_EXTRACTION_TOKEN = "__NEED_QT_EXTRACTION__"


class QtVideoFrameExtractor(QObject):
    """主线程：用 QMediaPlayer + QVideoSink 抽取视频帧（无需 ffmpeg）。"""

    progress = Signal(int, int)
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, media_path: str, out_dir: str,
                 max_frames: int = MAX_FRAME_COUNT, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.media_path = media_path
        self.out_dir = out_dir
        self.max_frames = max_frames

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._audio.setMuted(True)
        self._player.setAudioOutput(self._audio)
        self._sink = QVideoSink(self)
        self._player.setVideoSink(self._sink)
        self._sink.videoFrameChanged.connect(self._on_video_frame)

        self._targets: List[int] = []      # 期望的时间点(ms)
        self._saved: List[str] = []
        self._current_index = 0
        self._duration = 0
        self._busy = False
        self._done = False

        self._watchdog = QTimer(self)
        self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(self._on_watchdog)

    # public ------------------------------------------------------------------
    def extract(self):
        self._saved = []
        self._current_index = 0
        self._targets = []
        self._done = False
        os.makedirs(self.out_dir, exist_ok=True)
        self._player.setSource(QUrl.fromLocalFile(os.path.abspath(self.media_path)))
        self._player.mediaStatusChanged.connect(self._on_status)
        # 兜底：15 秒内无进展则失败
        self._watchdog.start(15000)

    def cancel(self):
        self._cleanup()
        if not self._done:
            self._done = True
            self.failed.emit("已取消")

    # private -----------------------------------------------------------------
    def _cleanup(self):
        try:
            self._watchdog.stop()
            self._player.mediaStatusChanged.disconnect(self._on_status)
        except (RuntimeError, TypeError):
            pass
        self._player.stop()

    @Slot()
    def _on_status(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia and not self._targets:
            self._duration = int(self._player.duration())
            if self._duration <= 0:
                # 无法读取时长：尝试直接播放一帧
                self._duration = 1000
            count = max(2, min(self.max_frames, 60))
            step = max(1, self._duration // count)
            self._targets = list(range(0, self._duration, step))[:count]
            logger.debug(f"Qt 抽帧：duration={self._duration}ms, targets={len(self._targets)}")
            self._seek_next()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._finish_fail(f"无法解码视频: {self._player.errorString() or '未知错误'}")

    def _seek_next(self):
        if self._current_index >= len(self._targets):
            self._finish_ok()
            return
        self._busy = True
        self._player.setPosition(self._targets[self._current_index])
        self._watchdog.start(5000)

    @Slot(object)
    def _on_video_frame(self, frame):
        if self._done or not self._busy:
            return
        try:
            image = frame.toImage()
            if image.isNull():
                return
            # 部分后端 seek 后会先给旧帧，这里不严格校验时间点，顺序保存即可
            out_path = os.path.join(self.out_dir, f"frame_{self._current_index:04d}.jpg")
            if image.save(out_path, "JPEG", 90):
                self._saved.append(out_path)
                self.progress.emit(self._current_index + 1, len(self._targets))
            self._current_index += 1
            self._busy = False
            if self._current_index >= len(self._targets):
                self._finish_ok()
            else:
                QTimer.singleShot(30, self._seek_next)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"保存视频帧失败: {e}")

    @Slot()
    def _on_watchdog(self):
        if self._done:
            return
        if self._saved:
            # 已经拿到部分帧就当作成功
            self._finish_ok()
        else:
            self._finish_fail("视频抽帧超时（可能缺少解码器）")

    def _finish_ok(self):
        if self._done:
            return
        self._done = True
        self._cleanup()
        if self._saved:
            self.finished_ok.emit(list(self._saved))
        else:
            self.failed.emit("未能抽取到视频帧")

    def _finish_fail(self, message: str):
        if self._done:
            return
        self._done = True
        self._cleanup()
        self.failed.emit(message)


def _extract_video_ffmpeg(media_path: str, out_dir: str, max_frames: int,
                          progress: Callable[[int, int], None],
                          cancelled: Callable[[], bool]) -> Optional[List[str]]:
    """用 ffmpeg 抽帧；ffmpeg 不可用时返回 None。"""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None

    # 先探测时长
    duration = 0.0
    try:
        probe = shutil.which("ffprobe")
        if probe:
            r = subprocess.run(
                [probe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", media_path],
                capture_output=True, text=True, timeout=15)
            try:
                duration = float(r.stdout.strip())
            except ValueError:
                duration = 0.0
    except Exception:  # noqa: BLE001
        duration = 0.0

    fps_expr = "1"
    if duration > 0:
        target = min(max_frames, max(2, int(duration * DEFAULT_FPS)))
        fps_expr = f"{target / duration:.6f}"

    out_pattern = os.path.join(out_dir, "frame_%04d.jpg")
    cmd = [ffmpeg, "-y", "-i", media_path, "-vf", f"fps={fps_expr}",
           "-frames:v", str(max_frames), "-q:v", "3", out_pattern]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg 抽帧超时") from None
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 抽帧失败: {proc.stderr[-300:] if proc.stderr else proc.returncode}")

    frames = sorted(glob.glob(os.path.join(out_dir, "frame_*.jpg")))
    progress(len(frames), len(frames))
    return frames


# ---------------------------------------------------------------------------
# 逐帧轮播
# ---------------------------------------------------------------------------

class FrameCycleController(QObject):
    """按帧率定时切换壁纸。"""

    tick = Signal(int, int)   # index, total
    failed = Signal(str)      # 切换失败

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.frames: List[str] = []
        self._index = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next)

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    def start(self, frames: List[str], fps: int = DEFAULT_FPS):
        if not frames:
            raise ValueError("帧列表为空")
        self.frames = list(frames)
        self._index = 0
        interval = max(1000 // max(MIN_FPS, min(MAX_FPS, fps)), 50)
        # 立即显示第一帧；失败则中止启动（错误通过返回值抛给调用方）
        if not self._show(0, emit_fail=False):
            raise RuntimeError("无法设置第一帧壁纸，请检查桌面环境是否受支持")
        self._timer.start(interval)
        logger.info(f"逐帧轮播启动: {len(self.frames)} 帧, {interval}ms/帧")

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()
        logger.debug("逐帧轮播已停止")

    def _next(self):
        if not self.frames:
            self.stop()
            return
        self._index = (self._index + 1) % len(self.frames)
        self._show(self._index)

    def _show(self, index: int, emit_fail: bool = True) -> bool:
        try:
            set_wallpaper_frame(self.frames[index])
            self.tick.emit(index + 1, len(self.frames))
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"切换壁纸帧失败: {e}")
            logger.debug(traceback.format_exc())
            self.stop()
            if emit_fail:
                self.failed.emit(str(e))
            return False


# ---------------------------------------------------------------------------
# Windows 桌面内嵌
# ---------------------------------------------------------------------------

def _windows_workerw_handle() -> Optional[int]:
    """返回可把窗口嵌入到桌面图标下方的 WorkerW 句柄。"""
    if platform.system() != "Windows":
        return None

    user32 = ctypes.windll.user32
    SMTO_NORMAL = 0x0000

    progman = user32.FindWindowW("Progman", None)
    if not progman:
        logger.error("未找到 Progman 窗口")
        return None

    result = ctypes.c_ulong()
    # 0x052C：让 Explorer 在图标层后方生成 WorkerW（未公开消息，Win7+ 通用）
    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, SMTO_NORMAL, 1000, ctypes.byref(result))

    # 方法一（经典）：找到含 SHELLDLL_DefView 的窗口，取其后一个 WorkerW 兄弟窗口
    found: List[int] = []

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _enum_proc(hwnd, _lparam):
        if user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
            sibling = user32.FindWindowExW(None, hwnd, "WorkerW", None)
            if sibling:
                found.append(sibling)
        return True

    try:
        user32.EnumWindows(WNDENUMPROC(_enum_proc), 0)
    except Exception:  # noqa: BLE001
        logger.debug(traceback.format_exc())

    if found:
        return found[0]

    # 方法二：遍历 WorkerW，找没有 DefView 的（部分 Win11 版本有效）
    hw = None
    cur = None
    while True:
        cur = user32.FindWindowExW(None, cur, "WorkerW", None)
        if not cur:
            break
        if not user32.FindWindowExW(cur, None, "SHELLDLL_DefView", None):
            hw = cur
    if hw:
        return hw

    # 方法三：退回 Progman（仍可能可用，需要配合 z-order 调整——此处简单回退）
    logger.warning("未找到专用 WorkerW，尝试使用 Progman 作为宿主")
    return progman


class DesktopEmbedWindow(QWidget):
    """无边框桌面宿主窗口：内嵌视频或 GIF 播放。"""

    def __init__(self, media_path: str, kind: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.media_path = media_path
        self.kind = kind
        self.workerw = 0
        self._attached = False

        # 注意：不要用 Qt.WindowType.Tool —— Tool 窗口会随主程序失焦而隐藏，不适合壁纸
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setStyleSheet("background-color: black;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout_safe(self)

        if kind == MEDIA_KIND_VIDEO:
            self.video_widget = QVideoWidget(self)
            self.video_widget.setStyleSheet("background: black;")
            layout.addWidget(self.video_widget)
            self.movie_label = None
            self.player = QMediaPlayer(self)
            self.audio = QAudioOutput(self)
            self.audio.setMuted(True)  # 壁纸默认静音
            self.player.setAudioOutput(self.audio)
            self.player.setVideoOutput(self.video_widget)
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(media_path)))
            self.player.setLoops(QMediaPlayer.Loops.Infinite)
            self.player.play()
        else:
            self.video_widget = None
            self.player = None
            self.movie_label = QLabel(self)
            self.movie_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.movie_label.setStyleSheet("background: black;")
            self.movie_label.setScaledContents(False)
            layout.addWidget(self.movie_label)
            from PySide6.QtGui import QMovie
            movie = QMovie(media_path, parent=self)
            movie.setCacheMode(QMovie.CacheMode.CacheAll)
            movie.setScaledSize(self.size())
            movie.start()
            self.movie = movie
            self.movie_label.setMovie(movie)

        # Explorer 重启后自动重新挂载
        self._health_timer = QTimer(self)
        self._health_timer.timeout.connect(self._check_health)
        self._health_timer.start(4000)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.kind != MEDIA_KIND_VIDEO and hasattr(self, "movie"):
            self.movie.setScaledSize(self.size())

    def attach_to_desktop(self) -> bool:
        if platform.system() != "Windows":
            return False
        user32 = ctypes.windll.user32
        workerw = _windows_workerw_handle()
        if not workerw:
            return False

        hwnd = int(self.winId())
        # 确保是分层窗口样式可用的顶层窗口再 SetParent
        result = user32.SetParent(hwnd, workerw)
        if result == 0 and ctypes.get_last_error():
            logger.error(f"SetParent 失败: {ctypes.get_last_error()}")
            return False

        # 铺满宿主（WorkerW 坐标为虚拟屏幕）
        rect = self._virtual_screen_rect()
        user32.MoveWindow(hwnd, rect[0], rect[1], rect[2], rect[3], True)
        # 提到 DefView（图标）之前，避免盖住图标：放到 HWND_BOTTOM 之上即可
        HWND_BOTTOM = 1
        SWP_NOACTIVATE = 0x0002
        SWP_FRAMECHANGED = 0x0010
        user32.SetWindowPos(hwnd, HWND_BOTTOM, rect[0], rect[1], rect[2], rect[3],
                            SWP_NOACTIVATE | SWP_FRAMECHANGED)

        self.workerw = workerw
        self._attached = True
        self.show()
        logger.info(f"动态壁纸已内嵌到桌面 WorkerW=0x{workerw:X}")
        return True

    def detach_from_desktop(self):
        if platform.system() != "Windows":
            return
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            user32.SetParent(hwnd, 0)
            self._attached = False
        except Exception:  # noqa: BLE001
            logger.debug(traceback.format_exc())

    def _virtual_screen_rect(self):
        user32 = ctypes.windll.user32
        SM_XVIRTUALSCREEN = 76
        SM_YVIRTUALSCREEN = 77
        SM_CXVIRTUALSCREEN = 78
        SM_CYVIRTUALSCREEN = 79
        return (
            user32.GetSystemMetrics(SM_XVIRTUALSCREEN),
            user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
            user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
            user32.GetSystemMetrics(SM_CYVIRTUALSCREEN),
        )

    def _check_health(self):
        if not self._attached or platform.system() != "Windows":
            return
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            if not user32.IsWindow(self.workerw):
                logger.warning("桌面 WorkerW 消失（可能 Explorer 已重启），尝试重新挂载")
                self.attach_to_desktop()
                return
            if user32.GetParent(hwnd) != self.workerw:
                self.attach_to_desktop()
        except Exception:  # noqa: BLE001
            logger.debug(traceback.format_exc())

    def shutdown(self):
        self._health_timer.stop()
        if self.player:
            try:
                self.player.stop()
                self.player.setSource(QUrl())
            except Exception:  # noqa: BLE001
                pass
        if hasattr(self, "movie") and self.movie:
            self.movie.stop()
        self.detach_from_desktop()
        self.close()
        self.deleteLater()


def QVBoxLayout_safe(widget: QWidget):
    from PySide6.QtWidgets import QVBoxLayout
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    return layout


# ---------------------------------------------------------------------------
# 引擎
# ---------------------------------------------------------------------------

class DynamicWallpaperEngine(QObject):
    """动态壁纸引擎：统一调度内嵌播放与逐帧轮播。"""

    status_changed = Signal(str)     # 状态文本（给 UI）
    busy_changed = Signal(bool)      # 是否正在处理（抽帧等）
    running_changed = Signal(bool)   # 是否在运行
    error_occurred = Signal(str)     # 错误信息

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._running = False
        self._busy = False
        self._mode_used: Optional[str] = None
        self._media_path: Optional[str] = None

        self._embed_window: Optional[DesktopEmbedWindow] = None
        self._frame_controller = FrameCycleController(self)
        self._frame_controller.failed.connect(self._on_frame_cycle_failed)
        self._extract_worker: Optional[FrameExtractionWorker] = None
        self._qt_extractor: Optional[QtVideoFrameExtractor] = None
        self._pending_fps = DEFAULT_FPS
        self._frames_dir = ""
        self._qt_fallback_tried = False

    # -- properties ------------------------------------------------------------
    @property
    def running(self) -> bool:
        return self._running

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def mode_used(self) -> Optional[str]:
        return self._mode_used

    @property
    def media_path(self) -> Optional[str]:
        return self._media_path

    # -- 对外 API --------------------------------------------------------------
    def resolve_mode(self, requested: str, kind: str) -> str:
        """把用户请求的模式解析为实际策略。"""
        system = platform.system()
        if requested == MODE_EMBED:
            if system != "Windows":
                raise RuntimeError("桌面内嵌播放目前仅支持 Windows，请改用逐帧轮播或自动模式")
            return MODE_EMBED
        if requested == MODE_FRAME:
            return MODE_FRAME
        # auto
        if system == "Windows":
            return MODE_EMBED
        return MODE_FRAME

    def apply(self, media_path: str, mode: str = MODE_AUTO, fps: int = DEFAULT_FPS) -> None:
        """应用动态壁纸（会先停止当前的）。"""
        if not media_path or not os.path.isfile(media_path):
            raise FileNotFoundError("媒体文件不存在")

        kind = detect_media_kind(media_path)
        if kind == MEDIA_KIND_UNSUPPORTED:
            raise ValueError("不支持的媒体格式：请选择视频（mp4/webm 等）或动图（GIF/APNG/动态 WebP）")

        resolved = self.resolve_mode(mode, kind)
        self.stop(silent=True)

        self._media_path = media_path
        self._pending_fps = max(MIN_FPS, min(MAX_FPS, int(fps or DEFAULT_FPS)))

        if resolved == MODE_EMBED:
            self._start_embed(media_path, kind)
        else:
            self._start_frame_cycle(media_path, kind)

    def stop(self, silent: bool = False):
        """停止动态壁纸。"""
        was_running = self._running

        if self._embed_window:
            try:
                self._embed_window.shutdown()
            except Exception:  # noqa: BLE001
                logger.debug(traceback.format_exc())
            self._embed_window = None

        if self._frame_controller.running:
            self._frame_controller.stop()

        if self._extract_worker and self._extract_worker.isRunning():
            self._extract_worker.cancel()
            self._extract_worker.wait(2000)

        if self._qt_extractor:
            self._qt_extractor.cancel()
            self._qt_extractor = None

        self._qt_fallback_tried = False
        self._set_busy(False)
        self._running = False
        self._mode_used = None

        if was_running and not silent:
            self.status_changed.emit("已停止")
        self.running_changed.emit(False)

    # -- 内嵌播放 --------------------------------------------------------------
    def _start_embed(self, media_path: str, kind: str):
        if platform.system() != "Windows":
            raise RuntimeError("内嵌播放仅支持 Windows")

        window = DesktopEmbedWindow(media_path, kind)
        if not window.attach_to_desktop():
            window.shutdown()
            raise RuntimeError("无法嵌入桌面（WorkerW 不可用），请尝试逐帧轮播模式")

        self._embed_window = window
        self._running = True
        self._mode_used = MODE_EMBED
        mode_name = "视频" if kind == MEDIA_KIND_VIDEO else "动图"
        self.status_changed.emit(f"运行中 · 桌面内嵌播放（{mode_name}）")
        self.running_changed.emit(True)

    # -- 逐帧轮播 --------------------------------------------------------------
    def _start_frame_cycle(self, media_path: str, kind: str):
        self._set_busy(True)
        self._qt_fallback_tried = False
        self.status_changed.emit("正在准备帧……")

        digest = hashlib.md5(os.path.abspath(media_path).encode("utf-8")).hexdigest()[:12]
        # 帧目录放在系统临时目录，避免污染图片目录
        import tempfile
        self._frames_dir = os.path.join(tempfile.gettempdir(), "wallpaper-generator-next",
                                        f"frames_{digest}")

        # 1) 动图：后台线程抽帧
        if kind == MEDIA_KIND_ANIMATED_IMAGE:
            worker = FrameExtractionWorker(media_path, self._frames_dir, kind,
                                           max_frames=MAX_FRAME_COUNT, parent=self)
            worker.progress.connect(self._on_extract_progress)
            worker.finished_ok.connect(self._on_frames_ready)
            worker.failed.connect(self._on_extract_failed)
            self._extract_worker = worker
            worker.start()
            return

        # 2) 视频：先试 ffmpeg（线程内），失败回退 Qt 主线程抽帧
        worker = FrameExtractionWorker(media_path, self._frames_dir, kind,
                                       max_frames=MAX_FRAME_COUNT, parent=self)
        worker.progress.connect(self._on_extract_progress)
        worker.finished_ok.connect(self._on_frames_ready)
        worker.failed.connect(self._on_extract_failed)
        self._extract_worker = worker
        worker.start()

    @Slot(int, int)
    def _on_extract_progress(self, current: int, total: int):
        self.status_changed.emit(f"正在抽帧…… {current}/{total}")

    @Slot(list)
    def _on_frames_ready(self, frames: List[str]):
        self._set_busy(False)
        try:
            self._frame_controller.start(frames, self._pending_fps)
            self._running = True
            self._mode_used = MODE_FRAME
            self.status_changed.emit(
                f"运行中 · 逐帧轮播（{len(frames)} 帧，{self._pending_fps} FPS）")
            self.running_changed.emit(True)
        except Exception as e:  # noqa: BLE001
            logger.error(f"启动逐帧轮播失败: {e}")
            logger.debug(traceback.format_exc())
            self._set_busy(False)
            self.error_occurred.emit(str(e))
            self.status_changed.emit("启动失败")

    @Slot(str)
    def _on_extract_failed(self, message: str):
        if message == "已取消":
            self._set_busy(False)
            return

        # 视频抽帧失败（缺 ffmpeg / ffmpeg 出错）→ 主线程降级到内置 Qt 解码器
        is_video = bool(self._extract_worker and
                        self._extract_worker.kind == MEDIA_KIND_VIDEO)
        if (message == NEED_QT_EXTRACTION_TOKEN or is_video) and \
                not self._qt_fallback_tried:
            logger.info(f"视频抽帧降级到 Qt 解码: {message}")
            self._qt_fallback_tried = True
            self._start_qt_video_extraction()
            return

        self._set_busy(False)
        self.error_occurred.emit(message)
        self.status_changed.emit(f"失败：{message}")

    def _start_qt_video_extraction(self):
        """ffmpeg 不可用时，主线程用 QVideoSink 抽帧。"""
        try:
            extractor = QtVideoFrameExtractor(
                self._media_path, self._frames_dir, max_frames=60, parent=self)
            extractor.progress.connect(self._on_extract_progress)
            extractor.finished_ok.connect(self._on_frames_ready)
            extractor.failed.connect(self._on_extract_failed)
            self._qt_extractor = extractor
            self.status_changed.emit("正在用内置解码器抽帧……")
            extractor.extract()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Qt 视频抽帧启动失败: {e}")
            logger.debug(traceback.format_exc())
            self._set_busy(False)
            self.error_occurred.emit(str(e))
            self.status_changed.emit(f"失败：{e}")

    @Slot(str)
    def _on_frame_cycle_failed(self, message: str):
        """逐帧轮播中途失败（如桌面环境拒绝设置壁纸）。"""
        self._running = False
        self._mode_used = None
        self.error_occurred.emit(message)
        self.status_changed.emit(f"失败：{message}")
        self.running_changed.emit(False)

    def _set_busy(self, value: bool):
        if self._busy != value:
            self._busy = value
            self.busy_changed.emit(value)

    # -- 退出清理 --------------------------------------------------------------
    def cleanup(self):
        """程序退出时调用。"""
        self.stop(silent=True)
        # 尽力清理临时帧目录（保留最近一次便于下次复用则删除更干净）
        if self._frames_dir and os.path.isdir(self._frames_dir):
            try:
                shutil.rmtree(self._frames_dir, ignore_errors=True)
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------------------
# 简单自测
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    engine = DynamicWallpaperEngine()
    engine.status_changed.connect(lambda s: print("status:", s))
    engine.error_occurred.connect(lambda e: print("error:", e))
    print("Windows workerw (non-win returns None):", _windows_workerw_handle())
    print("done")
