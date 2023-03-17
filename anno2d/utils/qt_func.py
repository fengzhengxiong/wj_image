# -*- coding: utf-8 -*-
# !/usr/bin/env python

from PyQt5 import QtWidgets, QtCore, QtGui

from PyQt5.QtWidgets import QPushButton, QAction, QMenu
from PyQt5.QtCore import QT_VERSION_STR, QRegExp
from PyQt5.QtGui import QColor, QIcon, QRegExpValidator
import hashlib

from anno2d.utils.pub import search_path_reference


def newIcon(icon, iconSize=None):
    if iconSize is not None:
        return QIcon(QIcon(':/' + icon).pixmap(iconSize, iconSize))
    else:
        return QIcon(':/' + icon)


def newButton(text, icon=None, slot=None):
    b = QPushButton(text)
    if icon is not None:
        b.setIcon(newIcon(icon))
    if slot is not None:
        b.clicked.connect(slot)
    return b


def newAction(
        parent,
        text,
        slot=None,
        shortcut=None,
        icon=None,
        tip=None,
        checkable=False,
        enabled=True,
        checked=False,
):
    """Create a new action and assign callbacks, shortcuts, etc."""
    a = QAction(text, parent)
    if icon is not None:
        a.setIconText(text.replace(" ", "\n"))
        a.setIcon(newIcon(icon))
    if shortcut is not None:
        if isinstance(shortcut, (list, tuple)):
            a.setShortcuts(shortcut)
        else:
            a.setShortcut(shortcut)
    if tip is not None:
        a.setToolTip(tip)
        a.setStatusTip(tip)
    if slot is not None:
        a.triggered.connect(slot)
    if checkable:
        a.setCheckable(True)
    a.setEnabled(enabled)
    a.setChecked(checked)
    return a


def addActions(widget, actions):
    for action in actions:
        if action is None:
            widget.addSeparator()
        elif isinstance(action, QMenu):
            widget.addMenu(action)
        else:
            widget.addAction(action)


def labelValidator():
    return QRegExpValidator(QRegExp(r'^[^ \t].+'), None)


def fmtShortcut(text):
    mod, key = text.split('+', 1)
    return '<b>%s</b>+<b>%s</b>' % (mod, key)


def generateColorByText(text):
    s = str(text)
    hashCode = int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16)
    r = int((hashCode / 255) % 255)
    g = int((hashCode / 65025) % 255)
    b = int((hashCode / 16581375) % 255)
    return QColor(r, g, b, 100)


def get_file_path(obj_wid=object, isfile=True, last_path=None, filter=''):
    """
    获取文件路径，适用于点击按钮，弹出对话框，确认后自动获取路径，功能仅支持单个文件或文件夹的选择
    :param obj_wid:  输入框之类的控件，支持人为输入了路径，供对话框检索定位
    :param isfile: 是否是文件
    :param last_path: 之前的路径，供支持快速检索
    :param filter: 文件类型过滤 eg. "All Files (*);;PDF Files (*.pdf);;Text Files (*.txt)
    :return: 输出的路径,如果出现异常失败，返回last_path
    """

    try:
        # 先试试obj_wid传入的对象是否靠谱
        if hasattr(obj_wid, "text"):
            obj_enable = True  # 控件对象使能，是可用的
        else:
            obj_enable = False
    except:
        obj_enable = False
    # print('obj_enable', obj_enable)

    default_path = last_path if last_path is not None else '.'
    if obj_enable:
        tmp_text = obj_wid.text()
        if tmp_text:
            default_path = tmp_text
    # print('default_path', default_path)

    ''' 判定一下框里的路径是否可以用来索引 '''
    res = search_path_reference(input_path=default_path, isfile=True)
    if res is not None:
        default_path = res

    input_path = ''  # 输入的路径，最终结果
    if isfile:
        ''' 文件 '''
        ret = QtWidgets.QFileDialog.getOpenFileName(caption='选择',
                                                    directory=default_path,
                                                    filter=filter)
        if ret[0] != '':
            input_path = ret[0]
        else:
            return last_path
    else:
        ''' 文件夹 '''
        ret = QtWidgets.QFileDialog.getExistingDirectory(caption='选择',
                                                         directory=default_path)
        if ret == "":
            return last_path
        input_path = ret

    if obj_enable:
        obj_wid.setText(input_path)
    return input_path
