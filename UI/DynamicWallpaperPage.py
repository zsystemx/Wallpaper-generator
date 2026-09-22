"""动态壁纸标签页

提供文件选择、实时预览、播放模式与帧率配置，以及应用/停止动态壁纸。
"""
from __future__ import annotations

import json
import os
import platform
import traceback

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QFileDialog, QLabel, QWidget
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from qfluentwidgets import InfoBar, InfoBarPosition

from Kernel.Logger import logger
from Kernel import MainKernal
from UI.DynamicWallpaperPage_ui import Ui_Form
from Kernel.DynamicWallpaperKernal import (
    DEFAULT_FPS,
    MAX_FPS,
    MEDIA_KIND_VIDEO,
    MIN_FPS,
    MODE_AUTO,
    MODE_EMBED,
    MODE_FRAME,
    DynamicWallpaperEngine,
    detect_media_kind,
)

MODE_ITEMS = [
    ("自动（推荐）", MODE_AUTO),
    ("桌面内嵌播放", MODE_EMBED),
    ("逐帧轮播", MODE_FRAME),
]


class DynamicWallpaperPage(QWidget, Ui_Form):
    """动态壁纸页面。"""

    stop_requested = Signal()   # 托盘等外部入口可触发停止

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.parent = parent

        self.engine = DynamicWallpaperEngine(self)
        self._media_path = ""
        self._preview_player = None
        self._preview_movie = None

        self._init_ui()
        self._load_settings()
        self.stop_requested.connect(self.on_stop)

    # ------------------------------------------------------------------ UI 初始化
    def _init_ui(self):
        system = platform.system()
        for label, mode_id in MODE_ITEMS:
            self.OptionMode.addItem(label)

        # 默认：Windows 上强调内嵌，其他系统强调逐帧
        default_index = 0
        self.OptionMode.setCurrentIndex(default_index)
        self.OptionMode.currentIndexChanged.connect(self._on_mode_changed)
        self._on_mode_changed(default_index)

        self.FpsSlider.setRange(MIN_FPS, MAX_FPS)
        self.FpsSlider.setValue(DEFAULT_FPS)
        self.FpsSlider.valueChanged.connect(self._on_fps_changed)

        self.ChoseFile.clicked.connect(self.on_choose_file)
        self.ApplyButton.clicked.connect(self.on_apply)
        self.StopButton.clicked.connect(self.on_stop)

        self.TextPath.textChanged.connect(self._on_path_changed)

        self.engine.status_changed.connect(self._on_status)
        self.engine.busy_changed.connect(self._on_busy)
        self.engine.error_occurred.connect(self._on_error)
        self.engine.running_changed.connect(self._on_running_changed)

    def _on_mode_changed(self, index: int):
        _, mode_id = MODE_ITEMS[max(0, index)]
        system = platform.system()
        if mode_id == MODE_EMBED:
            if system != "Windows":
                self.CaptionMode.setText("桌面内嵌播放仅支持 Windows；当前系统将无法应用该模式，请使用自动或逐帧轮播。")
            else:
                self.CaptionMode.setText("把播放窗口嵌入桌面图标下方循环播放（视频默认静音）。")
            self.FpsSlider.setEnabled(False)
        elif mode_id == MODE_FRAME:
            self.CaptionMode.setText("把媒体拆成帧按设定帧率循环切换壁纸，兼容 Windows / Linux / macOS。")
            self.FpsSlider.setEnabled(True)
        else:
            if system == "Windows":
                self.CaptionMode.setText("自动：优先使用桌面内嵌播放，失败时自动降级为逐帧轮播。")
                self.FpsSlider.setEnabled(True)  # 降级时会用到
            else:
                self.CaptionMode.setText("自动：当前系统使用逐帧轮播模式。")
                self.FpsSlider.setEnabled(True)

    def _on_fps_changed(self, value: int):
        self.FpsValue.setText(f"{value} FPS")

    def _on_path_changed(self, text: str):
        # 路径变化时（手动输入或选择）刷新预览
        path = text.strip().strip('"')
        if path and os.path.isfile(path):
            if path != self._media_path:
                self._media_path = path
                self._start_preview(path)
        else:
            self._stop_preview()

    # ---------------------------------------------------------------- 文件选择
    def on_choose_file(self):
        start_dir = os.path.dirname(self._media_path) if self._media_path else ""
        file_filter = (
            "媒体文件 (*.mp4 *.webm *.mkv *.avi *.mov *.wmv *.m4v *.flv *.mpeg *.mpg *.ts "
            "*.gif *.webp *.png *.apng);;所有文件 (*)"
        )
        path, _ = QFileDialog.getOpenFileName(self, "选择动态壁纸文件", start_dir, file_filter)
        if not path:
            return
        self.TextPath.setText(path)
        kind = detect_media_kind(path)
        if kind == "unsupported":
            self._show_error("格式不支持", "请选择视频文件或动态图片（GIF/APNG/动态 WebP）。")

    # ---------------------------------------------------------------- 预览
    def _stop_preview(self):
        if self._preview_player:
            try:
                self._preview_player.stop()
                self._preview_player.setSource(QUrl())
            except Exception:  # noqa: BLE001
                pass
            self._preview_player = None
        if self._preview_movie:
            try:
                self._preview_movie.stop()
            except Exception:  # noqa: BLE001
                pass
            self._preview_movie = None

        # 移除旧的预览控件（保留 Placeholder）
        layout = self.verticalLayout_preview
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            w = item.widget() if item else None
            if w and w is not self.PreviewPlaceholder:
                layout.takeAt(i)
                w.deleteLater()
        self.PreviewPlaceholder.show()

    def _start_preview(self, path: str):
        self._stop_preview()
        kind = detect_media_kind(path)
        if kind == "unsupported":
            self.PreviewPlaceholder.setText("无法预览：不支持的媒体格式")
            self.PreviewPlaceholder.show()
            return

        self.PreviewPlaceholder.hide()

        if kind == MEDIA_KIND_VIDEO:
            video = QVideoWidget()
            video.setStyleSheet("background: black; border-radius: 8px;")
            self.verticalLayout_preview.addWidget(video, stretch=1)
            player = QMediaPlayer(self)
            audio = QAudioOutput(self)
            audio.setMuted(True)
            player.setAudioOutput(audio)
            player.setVideoOutput(video)
            player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            player.setLoops(QMediaPlayer.Loops.Infinite)
            player.play()
            self._preview_player = player
        else:
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background: black; border-radius: 8px;")
            movie = QMovie(path, parent=self)
            movie.setCacheMode(QMovie.CacheMode.CacheAll)
            self.verticalLayout_preview.addWidget(label, stretch=1)
            label.setMovie(movie)
            movie.start()
            self._preview_movie = movie
            # 让 GIF 铺满预览区
            label.setMinimumSize(320, 200)

    # ---------------------------------------------------------------- 应用 / 停止
    def on_apply(self):
        path = self.TextPath.text().strip().strip('"')
        if not path or not os.path.isfile(path):
            self._show_error("无法应用", "请先选择一个存在的媒体文件。")
            return

        _, mode_id = MODE_ITEMS[max(0, self.OptionMode.currentIndex())]
        fps = self.FpsSlider.value()

        if mode_id == MODE_EMBED and platform.system() != "Windows":
            self._show_error("无法应用", "桌面内嵌播放仅支持 Windows，请选择自动或逐帧轮播。")
            return

        try:
            self.engine.apply(path, mode=mode_id, fps=fps)
            self._save_settings()
        except Exception as e:  # noqa: BLE001
            logger.error(f"应用动态壁纸失败: {e}")
            logger.debug(traceback.format_exc())
            self._show_error("应用失败", str(e))
            self._on_status(f"失败：{e}")

    def on_stop(self):
        self.engine.stop(silent=False)
        self._on_status("已停止")

    # ---------------------------------------------------------------- 引擎回调
    def _on_status(self, text: str):
        self.CurrentStage.setText(f" {text}")

    def _on_busy(self, busy: bool):
        self.ProgressLine.setVisible(busy)
        if busy:
            self.ProgressLine.start()
        else:
            self.ProgressLine.stop()
        self.ApplyButton.setEnabled(not busy)

    def _on_error(self, message: str):
        self._show_error("动态壁纸出错", message)

    def _on_running_changed(self, running: bool):
        self.StopButton.setEnabled(running)
        if running:
            self.ApplyButton.setText("重新应用")
        else:
            self.ApplyButton.setText("应用动态壁纸")

    def _show_error(self, title: str, content: str):
        InfoBar.error(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=5000,
            parent=self,
        )

    # ---------------------------------------------------------------- 持久化
    def _settings_path(self) -> str:
        return os.path.join(MainKernal.get_config_dir(), "dynamic_wallpaper.json")

    def _load_settings(self):
        path = self._settings_path()
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                file_path = data.get("path", "")
                if file_path and os.path.isfile(file_path):
                    # setText 会触发 textChanged → 自动启动预览
                    self.TextPath.setText(file_path)
                    self._media_path = file_path
                mode = data.get("mode", MODE_AUTO)
                for i, (_, mode_id) in enumerate(MODE_ITEMS):
                    if mode_id == mode:
                        self.OptionMode.setCurrentIndex(i)
                        self._on_mode_changed(i)
                        break
                fps = int(data.get("fps", DEFAULT_FPS))
                self.FpsSlider.setValue(max(MIN_FPS, min(MAX_FPS, fps)))
        except Exception:  # noqa: BLE001
            logger.debug(f"加载动态壁纸设置失败: {traceback.format_exc()}")

    def _save_settings(self):
        data = {
            "path": self.TextPath.text().strip().strip('"'),
            "mode": MODE_ITEMS[max(0, self.OptionMode.currentIndex())][1],
            "fps": self.FpsSlider.value(),
        }
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:  # noqa: BLE001
            logger.debug(f"保存动态壁纸设置失败: {traceback.format_exc()}")

    # ---------------------------------------------------------------- 生命周期
    def stop_wallpaper(self, silent: bool = True):
        """供主窗口退出/清理时调用。"""
        self._stop_preview()
        self.engine.stop(silent=silent)
        self.engine.cleanup()

    def closeEvent(self, event):
        super().closeEvent(event)
