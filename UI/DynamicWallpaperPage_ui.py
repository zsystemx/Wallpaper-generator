# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'DynamicWallpaperPage.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPalette,
    QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

from qfluentwidgets import (BodyLabel, CaptionLabel, ComboBox, IndeterminateProgressBar,
    LineEdit, OpacityAniStackedWidget, PrimaryPushButton, PushButton,
    SimpleCardWidget, Slider, SmoothScrollArea, StrongBodyLabel, SubtitleLabel)
import V4Resources_rc

class Ui_Form(object):
    def setupUi(self, Form: QWidget):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(1008, 668)
        Form.setStyleSheet(u"border-image: url(:/PNG/PNG/oyama-mahiro-ai~1.png);")
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.OpacityAniStackedWidget = OpacityAniStackedWidget(Form)
        self.OpacityAniStackedWidget.setObjectName(u"OpacityAniStackedWidget")
        self.OpacityAniStackedWidget.setStyleSheet(u"border-image: transparent;\n"
"background: transparent;")
        self.DynamicWallpaper_Page = QWidget()
        self.DynamicWallpaper_Page.setObjectName(u"DynamicWallpaper_Page")
        self.horizontalLayout_main = QHBoxLayout(self.DynamicWallpaper_Page)
        self.horizontalLayout_main.setObjectName(u"horizontalLayout_main")

        # ---------- 左侧：控制面板 ----------
        self.SimpleCardWidget = SimpleCardWidget(self.DynamicWallpaper_Page)
        self.SimpleCardWidget.setObjectName(u"SimpleCardWidget")
        self.SimpleCardWidget.setMinimumSize(QSize(360, 0))
        self.SimpleCardWidget.setMaximumSize(QSize(380, 16777215))
        self.verticalLayout_left = QVBoxLayout(self.SimpleCardWidget)
        self.verticalLayout_left.setObjectName(u"verticalLayout_left")
        self.verticalLayout_left.setContentsMargins(4, 4, 4, 4)

        self.SmoothScrollArea = SmoothScrollArea(self.SimpleCardWidget)
        self.SmoothScrollArea.setObjectName(u"SmoothScrollArea")
        self.SmoothScrollArea.setStyleSheet(u"background: transparent;\n"
"border: none;")
        self.SmoothScrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 340, 600))
        self.verticalLayout_2 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")

        self.SubtitleLabel = SubtitleLabel(self.scrollAreaWidgetContents)
        self.SubtitleLabel.setObjectName(u"SubtitleLabel")
        font = QFont()
        font.setFamilies([u"HarmonyOS Sans SC"])
        font.setPointSize(20)
        font.setBold(False)
        self.SubtitleLabel.setFont(font)
        self.SubtitleLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout_2.addWidget(self.SubtitleLabel)

        self.verticalSpacer_hint = QSpacerItem(20, 8, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout_2.addItem(self.verticalSpacer_hint)

        self.CaptionHint = CaptionLabel(self.scrollAreaWidgetContents)
        self.CaptionHint.setObjectName(u"CaptionHint")
        self.CaptionHint.setWordWrap(True)
        self.CaptionHint.setAlignment(Qt.AlignJustify|Qt.AlignTop)

        self.verticalLayout_2.addWidget(self.CaptionHint)

        self.verticalSpacer_1 = QSpacerItem(20, 16, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout_2.addItem(self.verticalSpacer_1)

        self.StrongBodyLabel_File = StrongBodyLabel(self.scrollAreaWidgetContents)
        self.StrongBodyLabel_File.setObjectName(u"StrongBodyLabel_File")

        self.verticalLayout_2.addWidget(self.StrongBodyLabel_File)

        self.horizontalLayout_file = QHBoxLayout()
        self.horizontalLayout_file.setObjectName(u"horizontalLayout_file")
        self.TextPath = LineEdit(self.scrollAreaWidgetContents)
        self.TextPath.setObjectName(u"TextPath")
        self.TextPath.setPlaceholderText(QCoreApplication.translate("Form", u"选择视频或动图文件…", None))

        self.horizontalLayout_file.addWidget(self.TextPath)

        self.ChoseFile = PushButton(self.scrollAreaWidgetContents)
        self.ChoseFile.setObjectName(u"ChoseFile")
        self.ChoseFile.setMinimumSize(QSize(88, 0))

        self.horizontalLayout_file.addWidget(self.ChoseFile)

        self.verticalLayout_2.addLayout(self.horizontalLayout_file)

        self.verticalSpacer_2 = QSpacerItem(20, 14, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout_2.addItem(self.verticalSpacer_2)

        self.StrongBodyLabel_Mode = StrongBodyLabel(self.scrollAreaWidgetContents)
        self.StrongBodyLabel_Mode.setObjectName(u"StrongBodyLabel_Mode")

        self.verticalLayout_2.addWidget(self.StrongBodyLabel_Mode)

        self.OptionMode = ComboBox(self.scrollAreaWidgetContents)
        self.OptionMode.setObjectName(u"OptionMode")

        self.verticalLayout_2.addWidget(self.OptionMode)

        self.CaptionMode = CaptionLabel(self.scrollAreaWidgetContents)
        self.CaptionMode.setObjectName(u"CaptionMode")
        self.CaptionMode.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.CaptionMode)

        self.verticalSpacer_3 = QSpacerItem(20, 14, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout_2.addItem(self.verticalSpacer_3)

        self.StrongBodyLabel_Fps = StrongBodyLabel(self.scrollAreaWidgetContents)
        self.StrongBodyLabel_Fps.setObjectName(u"StrongBodyLabel_Fps")

        self.verticalLayout_2.addWidget(self.StrongBodyLabel_Fps)

        self.horizontalLayout_fps = QHBoxLayout()
        self.horizontalLayout_fps.setObjectName(u"horizontalLayout_fps")
        self.FpsSlider = Slider(self.scrollAreaWidgetContents)
        self.FpsSlider.setObjectName(u"FpsSlider")
        self.FpsSlider.setOrientation(Qt.Horizontal)

        self.horizontalLayout_fps.addWidget(self.FpsSlider)

        self.horizontalSpacer_fps = QSpacerItem(8, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.horizontalLayout_fps.addItem(self.horizontalSpacer_fps)

        self.FpsValue = BodyLabel(self.scrollAreaWidgetContents)
        self.FpsValue.setObjectName(u"FpsValue")
        self.FpsValue.setMinimumSize(QSize(72, 0))

        self.horizontalLayout_fps.addWidget(self.FpsValue)

        self.verticalLayout_2.addLayout(self.horizontalLayout_fps)

        self.verticalSpacer_4 = QSpacerItem(20, 14, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout_2.addItem(self.verticalSpacer_4)

        self.StrongBodyLabel_Status = StrongBodyLabel(self.scrollAreaWidgetContents)
        self.StrongBodyLabel_Status.setObjectName(u"StrongBodyLabel_Status")

        self.verticalLayout_2.addWidget(self.StrongBodyLabel_Status)

        self.CurrentStage = SubtitleLabel(self.scrollAreaWidgetContents)
        self.CurrentStage.setObjectName(u"CurrentStage")
        font1 = QFont()
        font1.setFamilies([u"HarmonyOS Sans SC Medium"])
        font1.setPointSize(12)
        font1.setBold(False)
        self.CurrentStage.setFont(font1)
        self.CurrentStage.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.CurrentStage)

        self.ProgressLine = IndeterminateProgressBar(self.scrollAreaWidgetContents)
        self.ProgressLine.setObjectName(u"ProgressLine")
        self.ProgressLine.setVisible(False)

        self.verticalLayout_2.addWidget(self.ProgressLine)

        self.verticalSpacer_grow = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(self.verticalSpacer_grow)

        self.horizontalLayout_buttons = QHBoxLayout()
        self.horizontalLayout_buttons.setObjectName(u"horizontalLayout_buttons")
        self.StopButton = PushButton(self.scrollAreaWidgetContents)
        self.StopButton.setObjectName(u"StopButton")
        self.StopButton.setEnabled(False)

        self.horizontalLayout_buttons.addWidget(self.StopButton)

        self.ApplyButton = PrimaryPushButton(self.scrollAreaWidgetContents)
        self.ApplyButton.setObjectName(u"ApplyButton")

        self.horizontalLayout_buttons.addWidget(self.ApplyButton)

        self.verticalLayout_2.addLayout(self.horizontalLayout_buttons)

        self.verticalSpacer_bottom = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout_2.addItem(self.verticalSpacer_bottom)

        self.SmoothScrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_left.addWidget(self.SmoothScrollArea)

        self.horizontalLayout_main.addWidget(self.SimpleCardWidget)

        # ---------- 右侧：预览 ----------
        self.SimpleCardWidget_2 = SimpleCardWidget(self.DynamicWallpaper_Page)
        self.SimpleCardWidget_2.setObjectName(u"SimpleCardWidget_2")
        self.verticalLayout_right = QVBoxLayout(self.SimpleCardWidget_2)
        self.verticalLayout_right.setObjectName(u"verticalLayout_right")

        self.PreviewTitle = SubtitleLabel(self.SimpleCardWidget_2)
        self.PreviewTitle.setObjectName(u"PreviewTitle")
        self.PreviewTitle.setAlignment(Qt.AlignCenter)

        self.verticalLayout_right.addWidget(self.PreviewTitle)

        self.verticalSpacer_p1 = QSpacerItem(20, 6, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout_right.addItem(self.verticalSpacer_p1)

        self.PreviewStack = QWidget(self.SimpleCardWidget_2)
        self.PreviewStack.setObjectName(u"PreviewStack")
        self.PreviewStack.setStyleSheet(u"background-color: rgba(0, 0, 0, 0.72);\n"
"border-radius: 8px;")
        self.verticalLayout_preview = QVBoxLayout(self.PreviewStack)
        self.verticalLayout_preview.setObjectName(u"verticalLayout_preview")
        self.verticalLayout_preview.setContentsMargins(0, 0, 0, 0)

        self.PreviewPlaceholder = BodyLabel(self.PreviewStack)
        self.PreviewPlaceholder.setObjectName(u"PreviewPlaceholder")
        self.PreviewPlaceholder.setAlignment(Qt.AlignCenter)
        self.PreviewPlaceholder.setWordWrap(True)

        self.verticalLayout_preview.addWidget(self.PreviewPlaceholder, stretch=1)

        self.verticalLayout_right.addWidget(self.PreviewStack, stretch=1)

        self.verticalSpacer_p2 = QSpacerItem(20, 8, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.verticalLayout_right.addItem(self.verticalSpacer_p2)

        self.CaptionPreview = CaptionLabel(self.SimpleCardWidget_2)
        self.CaptionPreview.setObjectName(u"CaptionPreview")
        self.CaptionPreview.setAlignment(Qt.AlignCenter)
        self.CaptionPreview.setWordWrap(True)

        self.verticalLayout_right.addWidget(self.CaptionPreview)

        self.horizontalLayout_main.addWidget(self.SimpleCardWidget_2, stretch=1)

        self.OpacityAniStackedWidget.addWidget(self.DynamicWallpaper_Page)
        self.verticalLayout.addWidget(self.OpacityAniStackedWidget)

        self.retranslateUi(Form)
        self.OpacityAniStackedWidget.setCurrentIndex(0)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.SubtitleLabel.setText(QCoreApplication.translate("Form", u"动态壁纸", None))
        self.CaptionHint.setText(QCoreApplication.translate("Form", u"选择一段视频或一张动图，让它在桌面上动起来。Windows 下优先使用桌面内嵌播放（图标下方循环播放、不打断操作）；其他系统或内嵌失败时自动降级为逐帧轮播。", None))
        self.StrongBodyLabel_File.setText(QCoreApplication.translate("Form", u"媒体文件", None))
        self.ChoseFile.setText(QCoreApplication.translate("Form", u"选择 ", None))
        self.StrongBodyLabel_Mode.setText(QCoreApplication.translate("Form", u"播放模式", None))
        self.CaptionMode.setText(QCoreApplication.translate("Form", u"自动：Windows 使用内嵌播放，其他系统使用逐帧轮播。", None))
        self.StrongBodyLabel_Fps.setText(QCoreApplication.translate("Form", u"逐帧轮播帧率", None))
        self.FpsValue.setText(QCoreApplication.translate("Form", u"5 FPS", None))
        self.StrongBodyLabel_Status.setText(QCoreApplication.translate("Form", u"当前状态", None))
        self.CurrentStage.setText(QCoreApplication.translate("Form", u"未运行", None))
        self.StopButton.setText(QCoreApplication.translate("Form", u"停止动态壁纸", None))
        self.ApplyButton.setText(QCoreApplication.translate("Form", u"应用动态壁纸", None))
        self.PreviewTitle.setText(QCoreApplication.translate("Form", u"预览", None))
        self.PreviewPlaceholder.setText(QCoreApplication.translate("Form", u"尚未选择文件\n请点击左侧【选择】按钮打开视频或动图", None))
        self.CaptionPreview.setText(QCoreApplication.translate("Form", u"预览仅供查看；应用后才会真正设置到桌面。退出程序会停止动态壁纸。", None))
    # retranslateUi
