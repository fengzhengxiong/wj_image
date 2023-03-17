# !/usr/bin/env python
# -*- coding: utf-8 -*-


from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


from anno2d.widgets.canvas import Canvas
import sys
import math
import numpy as np
import cv2

from anno2d.utils.image_util import *


class DrawBoard(QWidget):
    zoomMsg = pyqtSignal(tuple)  # 缩放消息发送

    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2

    ZOOM_MAX = 3000  # 最大放大倍数
    ZOOM_MIN = 2  # 最小倍数
    SCROLLBAR_HIDE = False  # 下拉条是否隐藏



    def __init__(self, *args, **kwargs):
        super(DrawBoard, self).__init__(*args, **kwargs)
        self.resize(600, 400)
        self.initUI()

        self.scrollBars = {
            Qt.Vertical: self.scrollArea.verticalScrollBar(),
            Qt.Horizontal: self.scrollArea.horizontalScrollBar()
        }
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            self.MANUAL_ZOOM: lambda: 1,
        }

        self._zoom_val = 100
        self.zoomMode = self.FIT_WINDOW
        self.pixmap = None


    def initUI(self):
        """
        srcoll + canvas
        :return:
        """
        self.canvas = Canvas()  # 图像控件
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)  # 设置为true，则滚动区域部件将自动调整，以避免可以不显示的滚动条，或者利用额外的空间；
        self.scrollArea.setStyleSheet("QScrollArea{border:none; background:white;}")
        self.scrollArea.setWidget(self.canvas)

        if self.SCROLLBAR_HIDE:
            self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        lay = QHBoxLayout(self)
        lay.addWidget(self.scrollArea)
        lay.setContentsMargins(0, 0, 0, 0)

        self.canvas.zoomRequest.connect(self.zoomRequest)  # 图像鼠标缩放
        self.canvas.scrollRequest.connect(self.scrollRequest)
        #
        # self.canvas.newShape.connect(self.newShape)
        # self.canvas.shapeMoved.connect(self.updateLabelPoints)  # self.setDirty
        # self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        # self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)
        # self.canvas.coordChanged.connect(self.showPosition)

    def loadImage(self, data):
        if isinstance(data, QPixmap):
            self.pixmap = data
        elif isinstance(data, QImage):
            self.pixmap = qimage2qpixmap(data)
        elif isinstance(data, np.ndarray):
            self.pixmap = array2qpixmap(data)
        elif isinstance(data, str):
            self.pixmap = file2qpixmap(data)

        if self.pixmap:
            # self.setFitWindow()
            self.canvas.loadPixmap(QPixmap(self.pixmap))

    def reset(self):
        # self._zoom_val = 100
        # self.zoomMode = self.FIT_WINDOW
        self.pixmap = None
        self.canvas.resetState()

    def setZoom(self, value):
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        # self._zoom_val = value
        self._zoom_val = np.clip(value, self.ZOOM_MIN, self.ZOOM_MAX)
        self.paintCanvas()

    def getZoom(self):
        return self._zoom_val

    def addZoom(self, increment=1.1):
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        zoom_value = self.getZoom() * increment
        # if increment > 1:
        #     zoom_value = math.ceil(zoom_value)
        # else:
        #     zoom_value = math.floor(zoom_value)

        self.zoomMode = self.MANUAL_ZOOM
        self.setZoom(zoom_value)

    def zoomRequest(self, delta, pos):
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        try:
            canvas_width_old = self.canvas.width()
            units = 1.2 if delta > 0 else 0.8
            self.addZoom(units)
            # 更新图像偏移
            canvas_width_new = self.canvas.width()
            if canvas_width_old != canvas_width_new:
                canvas_scale_factor = canvas_width_new / canvas_width_old
                x_shift = round(pos.x() * canvas_scale_factor) - pos.x()
                y_shift = round(pos.y() * canvas_scale_factor) - pos.y()
                self.setScroll(Qt.Horizontal, self.scrollBars[Qt.Horizontal].value() + x_shift)
                self.setScroll(Qt.Vertical, self.scrollBars[Qt.Vertical].value() + y_shift)

            self.zoomMsg.emit((
                self.zoomMode,
                self.getZoom(),
                self.scrollBars[Qt.Horizontal].value(),
                self.scrollBars[Qt.Vertical].value()))
        except Exception as e:
            print(e)

    def scrollRequest(self, delta, orientation, drag=False):
        """
        移动图像
        :param delta: 值
        :param orientation: 方向
        :param drag: True 是鼠标移动图片，False 是滚轮操作
        :return:
        """
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)

        bar = self.scrollBars[orientation]
        if not drag:
            '''滚轮'''
            units = -delta * 0.02  # natural scroll
            # units = - delta / (8 * 15)
            value = bar.value() + bar.singleStep() * units
        else:
            units = -delta / 100
            value = bar.value() + bar.singleStep() * units
        self.setScroll(orientation, value)

        self.zoomMsg.emit((
            self.zoomMode,
            self.getZoom(),
            self.scrollBars[Qt.Horizontal].value(),
            self.scrollBars[Qt.Vertical].value()))

    def setScroll(self, orientation, value):
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        self.scrollBars[orientation].setValue(value)

    def scaleFitWindow(self):
        """Figure out the size of the pixmap to fit the main widget."""
        if self.pixmap is None:
            return

        e = 0.0 if self.SCROLLBAR_HIDE else 2.0
        w1 = self.scrollArea.width() - e
        h1 = self.scrollArea.height() - e

        a1 = w1 / h1
        w2 = self.canvas.pixmap.width()
        h2 = self.canvas.pixmap.height()
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        if self.pixmap is None:
            return
        # TODO 实际尺寸考虑当前控件比例和图像比例，判定进度条是否显示，进度条宽度为17
        e = 0.0 if self.SCROLLBAR_HIDE else 2.0
        w = self.scrollArea.width() - e
        return w / self.canvas.pixmap.width()

    def setFitWindow(self, value=True):
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def adjustScale(self, initial=False):
        try:
            if self.pixmap is None:
                return
            value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
            value = (100 * value)
            self.setZoom(value)
        except Exception as e:
            print(e)

    def paintCanvas(self):
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        self.canvas.setScale(0.01 * self._zoom_val)
        self.canvas.adjustSize()
        self.canvas.update()

    def resizeEvent(self, event):
        if not self.canvas.pixmap.isNull() and self.zoomMode != self.MANUAL_ZOOM:
            self.adjustScale()
        super(DrawBoard, self).resizeEvent(event)

    def keyPressEvent(self, ev):
        # print('--keyPressEvent ')
        modifiers = ev.modifiers()
        key = ev.key()

        if key == Qt.Key_F:
            self.setFitWidth()
        elif key == Qt.Key_G:
            self.setFitWindow()

        # elif key == Qt.Key_L:
        #     bar = self.scrollArea.verticalScrollBar()
        #     bar2 = self.scrollArea.horizontalScrollBar()
        #     print(bar.width(), bar.height())
        #     print(bar2.width(), bar2.height())
        # elif key == Qt.Key_M:
        #     self.reset()



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = DrawBoard()
    win.resize(600,300)
    # win.loadImage(QPixmap('./7_2.png'))
    win.loadImage('./7_2.png')
    # win.setWindowIcon(QIcon("wanji_logo64.ico"))
    win.show()

    sys.exit(app.exec_())