# !/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt
from anno2d.data.filemsg import FileMsg


class FileListWidgetItem(QtWidgets.QListWidgetItem):

    normalFont = QtGui.QFont()
    normalColor = QtGui.QColor(0, 0, 0, 255)

    checkFont = QtGui.QFont()
    checkFont.setFamily("微软雅黑")
    checkFont.setBold(True)
    checkFont.setUnderline(True)
    checkColor = QtGui.QColor(0, 100, 0, 255)

    abandonFont = QtGui.QFont()
    abandonFont.setStrikeOut(True)
    abandonColor = QtGui.QColor(150, 150, 0, 255)

    def __init__(self, text=None, file=None):
        super(FileListWidgetItem, self).__init__()
        self.setText(text or "")
        self.setFile(file)

        self.setForeground(self.checkColor)
        self.setFont(self.checkFont)
        # self.setIcon()

    def setFileMode(self, state=FileMsg.normalState):
        if state == FileMsg.normalState:
            self.setForeground(self.normalColor)
            self.setFont(self.normalFont)
            # self.setIcon()
        elif state == FileMsg.checkState:
            self.setForeground(self.checkColor)
            self.setFont(self.checkFont)
        elif state == FileMsg.abandonState:
            self.setForeground(self.abandonColor)
            self.setFont(self.abandonFont)

    def clone(self):
        return FileListWidgetItem(self.text(), self.file())

    def setFile(self, file):
        self.setData(Qt.UserRole, file)

    def file(self):
        return self.data(Qt.UserRole)

    def __hash__(self):
        return id(self)

    def __repr__(self):
        return '{}("{}")'.format(self.__class__.__name__, self.text())