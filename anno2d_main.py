# -*- coding: utf-8 -*-
# !/usr/bin/env python


import sys
sys.setrecursionlimit(100000000)

import os

import os.path as osp
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
import cv2
import math
import argparse
import ast
import codecs
import base64

import platform
import subprocess
from functools import partial
from collections import defaultdict
import json
from PIL import Image
import time
import copy
import shutil
import random
import codecs

from anno2d import __version__, __appname__

from anno2d.utils.qt_func import *
from anno2d.utils.pub import *
from anno2d.utils.image import do_mosaic


from anno2d.widgets.canvas import Canvas
from anno2d.widgets.drawboard import DrawBoard
from anno2d.widgets.zoomWidget import ZoomWidget
from anno2d.widgets.tool_bar import ToolBar
from anno2d.widgets.file_list_widget import FileListWidgetItem
from anno2d.widgets.label_list_widget import LabelListWidget, LabelListWidgetItem
from anno2d.widgets.transfile_dialog import TransfileDialog
from anno2d.widgets.mainwindow_ui import Ui_MainWindow

from anno2d.data.filemsg import FileMsg
from anno2d.data.annomsg import AnnoMsg
from anno2d.data.shape import Shape
from anno2d.data.labelmsg import LabelMsg

from anno2d.utils.label_file import LabelFile, LabelFileError
from anno2d.utils.image_util import *


_title = __appname__ + ' v' + __version__

TEST_PATH = None
# TEST_PATH = r'C:\Users\wanji\Desktop\测试图'
TEST_PATH = r'D:\标注资料\01_图像标注软件\04 测试样本\测试图'

# import imgviz
#
# LABEL_COLORMAP = imgviz.label_colormap()

import colorsys

classes = 360
hsv_tuples = [(1.0 * x / classes, 1.0, 1.0) for x in range(classes)]
colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
LABEL_COLORMAP2 = list(map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)), colors))

License_Plate_Region = ['京', '津', '冀', '沪', '渝', '粤', '宁', '新', '藏', '桂', '蒙', '辽', '吉', '黑', '晋', '苏',
                        '浙', '皖', '闽', '赣', '鲁', '豫', '鄂', '湘', '琼', '川', '贵', '云', '陕', '甘', '青']

PLATE_COLOR_DICT = {
    0: '蓝',
    1: '黄',
    2: '绿',
    3: '白',
    4: '-'
}

class AppEntry(QMainWindow, Ui_MainWindow):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2

    CACHE = "cache"  # 软件缓存目录
    LABEL_CACHE = "label_cache"  # 子目录，标签文件
    LABEL_CHECK = "label_check"  # 子目录，标签check出来的文件，受到改变时，将删除这里的问题
    ANNO_STATE_NAME = "anno_state.json"  # 标注状态文件名称
    RECYCLE = "recycle"  # 子目录，回收站
    ORIGIN_IMG = "origin_img"  # 子目录， 存放原图
    OUTPUT = "output"  # 子目录,输出结果
    YOLO_RESULT = "yolo"  # 子目录
    YOLO_RESULT2 = "yolo2"  # 子目录


    DEFAULT_TYPE_MAP = {
        "person": 0,
        "none": 1,
        "bicycle": 201,
        "electric_bicycle": 301,
        "motorbike": 401,
        "bicycle_person": 202,
        "electric_bicycle_person": 302,
        "motorbike_person": 402,
        "tricycle": 5,
        "car": 6,
        "passenger_car": 7,
        "truck_h": 8,
        "truck_k": 901,
        "jtruck": 902,
        "tractors": 10,
        "bus": 11,
        "dump_truck": 12,
        "mixer_truck": 13,
        "tanker": 14,
        "sprinkler": 15,
        "fire_engine": 16,
        "police_car": 17,
        "ambulance": 18,
        "tool_vehicle": 19,
        "road_cone": 20
    }

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(_title)

        self.fileName = None  # 完整名称
        self.fileBaseName = None  # 图片名称
        self.imageList = []  # 图像列表，self.fileName * n
        self.fileDir = ''  # 文件夹路径
        self.lastOpenDir = None  # 上一次打开的文件夹
        self.lastOpenFile = None  # 上一次打开文件路径

        self.lastFileState = None  # 当前文件上一个文件状态
        self.labelShapes = []  # 当前图像文件标签列表 Shape() * n
        self.labelDict = {}  # key: 图片名称 value: self.labelShapes
        self.fileStateDict = {}  # 记录文件标注状态,k : xx.png  v: FileMsg()
        self.fileUpdateTimeDict = {}  # 标签文件更新时间戳，key: xx.png ,val: 时间
        self.fileAnnoDelayDict = {}  # 图标标注耗时，以打开到保存截止

        self.image = QImage()  # 当前图像对象
        self.pixmap = QPixmap()
        self.arrImage = None  # 当前图像原始np数据
        self.arrImageMosaic = None  # 当前打码图像

        self.annoMsg = None  # 当前图像的标注信息
        self.imageData = None  # 图像数据base64
        self.datasetName = None  # 数据集名称，暂无用

        # 记录没张图缩放位置情况，缩放在画板board里
        self.zoom_values = {}  # key=filename, value=(zoom_mode, zoom_value, hbar, vbar)
        self.brightnessContrast_values = {}
        self.scroll_values = {
            Qt.Horizontal: {},
            Qt.Vertical: {},
        }  # key=filename, value=scroll_value


        self.output_file = None
        self.output_dir = None

        self.beginTime, self.endTime = None, None

        self.dirty = False  # save or not
        self._noSelectionSlot = False
        self._noLabelEditSlot = False

        self._noFileSelectionSlot = False  # 文件的变更触发
        self._copied_shapes = None  # ctrl+c


        self.board = DrawBoard()  # 画板
        imgLayout = QVBoxLayout(self.imgFrame)
        imgLayout.addWidget(self.board)
        imgLayout.setContentsMargins(0, 0, 0, 0)

        self.board.zoomMsg.connect(self.updateZoom)

        self.board.canvas.newShape.connect(self.newShape)
        self.board.canvas.shapeMoved.connect(self.updateLabelPoints)  # self.setDirty
        self.board.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.board.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)
        self.board.canvas.coordChanged.connect(self.showPosition)

        self.labelList = LabelListWidget()
        labelLayout = QVBoxLayout(self.labelFrame)
        labelLayout.addWidget(self.labelList)
        labelLayout.setContentsMargins(0, 0, 0, 0)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        # self.labelList.itemDoubleClicked.connect(self.editLabel)
        self.labelList.itemChanged.connect(self.labelItemChanged)  # 勾选
        self.labelList.itemDropped.connect(self.labelOrderChanged)

        # self.fileListWidget = QListWidget()
        # filelistLayout = QVBoxLayout(self.FileFrame)
        # filelistLayout.addWidget(self.fileListWidget)
        # filelistLayout.setContentsMargins(0, 0, 0, 0)

        self.fileListWidget.itemSelectionChanged.connect(
            self.fileSelectionChanged
        )
        # Display cursor coordinates at the right of status bar
        self.labelCoordinates = QLabel('')
        self.statusBar().addPermanentWidget(self.labelCoordinates)


        self.zoomWidget = ZoomWidget()
        self.zoomWidget.setEnabled(False)

        self.initActions()
        labelMenu = QtWidgets.QMenu()
        addActions(labelMenu, (self.actions.edit, self.actions.delete))
        # self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.menus = struct(
            file=self.menu(self.tr("&File")),
            edit=self.menu(self.tr("&Edit")),
            view=self.menu(self.tr("&View")),
            help=self.menu(self.tr("&Help")),
            recentFiles=QtWidgets.QMenu(self.tr("Open &Recent")),
            labelList=labelMenu,
        )
        self.tools = self.toolbar("Tools")

        self.initMenus()

        self.populateModeActions()

        self.board.canvas.vertexSelected.connect(self.actions.removePoint.setEnabled)
        addActions(self.board.canvas.menus[0], self.actions.menu)
        addActions(self.board.canvas.menus[1], (self.actions.copyHere, self.actions.moveHere))


        # Lavel list context menu.
        labelMenu = QtWidgets.QMenu()
        addActions(labelMenu, (self.actions.edit, self.actions.delete))
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(
            self.popLabelListMenu
        )

        self.comboBox.setEnabled(False)
        self.comboBox_2.setEnabled(False)
        self.comboBox.addItems(License_Plate_Region)
        plate_color_text = [str(k) + '=' + str(v) for k, v in PLATE_COLOR_DICT.items()]

        self.comboBox_2.addItems(plate_color_text)
        # TODO item  setdata
        # for i in self.comboBox_2.count():
        #     self.comboBox_2.setItemData(i, int(i), Qt.UserRole)

        self.comboBox.setEnabled(True)
        self.comboBox_2.setEnabled(True)

        valid = QIntValidator(self)
        valid.setRange(0, 4)
        self.lineEdit_4.setValidator(valid)


        # TODO 按钮添加action 临时的
        self.toolButton_20.setDefaultAction(self.actions.editMode)
        self.toolButton_21.setDefaultAction(self.actions.createRectangleMode)
        self.toolButton_22.setDefaultAction(self.actions.mosaic)
        self.toolButton_23.setDefaultAction(self.actions.deMosaic)
        self.toolButton_2.setDefaultAction(self.actions.deleteAbandon)  # 还原文件
        self.toolButton_4.setDefaultAction(self.actions.recovery)  # 丢弃文件
        self.toolButton.setDefaultAction(self.actions.deleteImg)
        self.toolButton_15.setDefaultAction(self.actions.save)

        self.toolButton_19.setDefaultAction(self.actions.duplicate)
        self.toolButton_18.setDefaultAction(self.actions.delete)
        self.toolButton_17.setDefaultAction(self.actions.paste)
        self.toolButton_16.setDefaultAction(self.actions.copy)
        self.toolButton_14.setDefaultAction(self.actions.undo)

        self.toolButton_8.setDefaultAction(self.actions.openPrevImg)
        self.toolButton_11.setDefaultAction(self.actions.normal)
        self.toolButton_13.setDefaultAction(self.actions.abandon)
        self.toolButton_12.setDefaultAction(self.actions.check)
        self.toolButton_10.setDefaultAction(self.actions.openNextImg)

        self.listWidget_2.itemDoubleClicked.connect(self.changeLabelAndDisp)
        self.listWidget_2.setToolTip("双击可修改标签类别")

        # ------------文件信息显示区-----------
        self.label_2.setText("已完成：-")
        self.label_3.setText("待丢弃：-")
        self.label_4.setText("标注用时： -")
        self.label_5.setText("完成时间：-")

        # ------------- 标签编辑区触发------------
        self.pushButton.clicked.connect(self.getLabelAndDisp)
        self.lineEdit_2.textChanged.connect(self.changeLabelData)
        self.spinBox.valueChanged.connect(self.changeLabelData)
        self.spinBox_2.valueChanged.connect(self.changeLabelData)
        self.lineEdit_3.textChanged.connect(self.changeLabelData)
        self.lineEdit_4.textChanged.connect(self.changeLabelData)

        self.comboBox.currentTextChanged.connect(self.changePlateRegion)
        self.comboBox_2.currentIndexChanged.connect(self.changePlateColor)

        self.horizontalLayout.removeWidget(self.listWidget_2)
        self.horizontalLayout.removeWidget(self.listWidget_3)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.listWidget_2)
        splitter.addWidget(self.listWidget_3)
        self.horizontalLayout.addWidget(splitter)


        self.listWidget_3.clear()
        self.listWidget_3.addItems(
            [
                "rectangle",
                "polygon",
                "point",
                "line",
                "circle",
                "linestrip",
                "no_draw"
             ]
        )
        #  TODO 这块的逻辑不好，先取消功能
        # self.listWidget_3.itemDoubleClicked.connect(self.shapetypeSelectionChanged)



        # 读取配置类别文件
        here = osp.abspath('.')
        typefilepath = osp.join(here, "class.json")
        self.participantMap = self.loadTypeMap(typefilepath)  # 交通参与者映射
        if not bool(self.participantMap):
            self.participantMap = self.DEFAULT_TYPE_MAP
        # 刷新显示类别
        self.updateTypeListWidget()


        self.zoomMode = self.FIT_WINDOW
        # fitWindow.setChecked(Qt.Checked)

        if TEST_PATH is not None:
            self.importDirImages(TEST_PATH)


    def initActions(self):
        action = partial(newAction, self)
        quit = action(
            text=self.tr("退出"),
            slot=self.close,
            shortcut=None,
            tip="quit",
        )
        openImg = action(
            text=self.tr("打开文件"),
            slot=None,
            shortcut="Ctrl+O",
        )

        openDir = action(
            text=self.tr("打开文件夹"),
            slot=self.openDirDialog,
            shortcut="Ctrl+U",
            # icon="done",
        )

        importLabel = action(
            text=self.tr("导入标签"),
            slot=self.importLabel,
            shortcut=None,
        )

        importDir = action(
            text=self.tr("导入批量标签"),
            slot=None,
            shortcut=None,
            enabled=False,
        )

        openPrevImg = action(
            text=self.tr("上一个"),
            slot=self.openPrevImg,
            shortcut="PgUp",
        )

        openNextImg = action(
            text=self.tr("下一个"),
            slot=self.openNextImg,
            shortcut="PgDown",
        )

        recent = action(
            text=self.tr("最近访问文件"),
            slot=None,
            shortcut=None,
        )

        save = action(
            text=self.tr("保存"),
            slot=self.saveFile,
            shortcut="Ctrl+S",
        )

        saveAs = action(
            text=self.tr("另存为"),
            slot=None,
            shortcut=None,
        )

        export = action(
            text=self.tr("输出标注结果"),
            slot=self.exportCheckedLabel,
            shortcut="Ctrl+W",
        )
        # TODO 对于导出标签功能，后续将集中调整一下
        export2 = action(
            text=self.tr("输出标注结果2"),
            slot=self.exportCheckedLabel2,
            # shortcut="Ctrl+W",
        )


        exportAll = action(
            text=self.tr("导出所有标签"),
            slot=None,
            shortcut=None,
        )

        exportSetting = action(
            text=self.tr("导出设置"),
            slot=None,
            shortcut=None,
        )

        saveWithImageData = action(
            text="Save With Image Data",
            slot=self.enableSaveImageWithData,
            tip="Save image data in label file",
            checkable=True,
            checked=True,
        )

        check = action(
            text=self.tr("check"),
            slot=self.checkFile,
            shortcut="C",
        )

        abandon = action(
            text=self.tr("待丢弃"),
            slot=self.abandonFile,
            shortcut=None,
        )

        normal = action(
            text=self.tr("待编辑"),
            slot=self.normalFile,
            shortcut=None,
        )

        checkAll = action(
            text=self.tr("check所有文件"),
            slot=None,
            shortcut=None,
            enabled=False,
        )

        normalAll = action(
            text=self.tr("待编辑所有文件"),
            slot=None,
            shortcut=None,
            enabled=False,
        )

        deleteImg = action(
            text=self.tr("删除当前图像"),
            slot=self.deleteImg,
            shortcut=None,
            enabled=True,
        )

        deleteAbandon = action(
            text=self.tr("移除丢弃文件"),
            slot=None,
            shortcut=None,
            enabled=False,
        )

        recovery = action(
            text=self.tr("回收站还原文件"),
            slot=None,
            shortcut=None,
            enabled=False,
        )

        recoveryImg = action(
            text=self.tr("恢复原图"),
            slot=None,
            shortcut=None,
        )

        createPolyMode = action(
            text=self.tr("创建多边形"),
            slot=lambda: self.toggleDrawMode(Canvas.CREATE, createMode="polygon"),
            shortcut=None,
            enabled=False,
        )
        createRectangleMode = action(
            text=self.tr("创建矩形"),
            slot=lambda: self.toggleDrawMode(Canvas.CREATE, createMode="rectangle"),
            shortcut="E",
            enabled=False,
        )
        createCircleMode = action(
            text=self.tr("创建圆形"),
            slot=lambda: self.toggleDrawMode(Canvas.CREATE, createMode="circle"),
            shortcut=None,
            enabled=False,
        )
        createLineMode = action(
            text=self.tr("创建直线"),
            slot=lambda: self.toggleDrawMode(Canvas.CREATE, createMode="line"),
            shortcut=None,
            enabled=False,
        )
        createPointMode = action(
            text=self.tr("创建单点"),
            slot=lambda: self.toggleDrawMode(Canvas.CREATE, createMode="point"),
            shortcut=None,
            enabled=False,
        )
        createLineStripMode = action(
            text=self.tr("创建折线"),
            slot=lambda: self.toggleDrawMode(Canvas.CREATE, createMode="linestrip"),
            shortcut=None,
            enabled=False,
        )
        editMode = action(
            text=self.tr("编辑模式"),
            slot=self.setEditMode,
            shortcut="q",
            enabled=False,
        )

        collectMode = action(
            text=self.tr("框选模式"),
            slot=None,
            shortcut=None,
            enabled=False,
        )

        maskMode = action(
            text=self.tr("脱敏模式"),
            slot=self.setMosaicMode,
            shortcut=None,
            enabled=True,
        )

        duplicate = action(
            text=self.tr("拷贝"),
            slot=self.duplicateSelectedShape,
            shortcut="Ctrl+D",
            enabled=False,
        )

        copy = action(
            text=self.tr("复制"),
            slot=self.copySelectedShape,
            shortcut="Ctrl+C",
            enabled=False,
        )

        paste = action(
            text=self.tr("粘贴"),
            slot=self.pasteSelectedShape,
            shortcut="Ctrl+V",
            enabled=False,
        )

        delete = action(
            text=self.tr("删除"),
            slot=self.deleteSelectedShape,
            shortcut="Del",
            enabled=False,
        )

        removePoint = action(
            text=self.tr("删除点"),
            slot=self.removeSelectedPoint,
            shortcut="Backspace",
            enabled=False,
        )

        undoLastPoint = action(
            text=self.tr("Undo last point"),
            slot=self.board.canvas.undoLastPoint,
            shortcut="Ctrl+Z",
            enabled=False,
        )

        undo = action(
            text=self.tr("撤回"),
            slot=self.undoShapeEdit,
            shortcut="Ctrl+Z",
            enabled=False,
        )

        redo = action(
            text=self.tr("redo"),
            slot=self.redoShapeEdit,
            shortcut="Ctrl+Shift+Z",
            enabled=False,
        )

        autoTurnEdit = action(
            text=self.tr("自动复位编辑模式"),
            slot=None,
            shortcut=None,
            checkable=True,
            enabled=True,
            checked=True,
        )

        hideAll = action(
            text=self.tr("隐藏所有标签"),
            slot=partial(self.togglePolygons, False),
            shortcut=None,
            enabled=False,
        )

        showAll = action(
            text=self.tr("显示所有标签"),
            slot=partial(self.togglePolygons, True),
            shortcut=None,
            enabled=False,
        )

        showLabelText = action(
            text=self.tr("显示标签信息"),
            slot=self.toggleDrawText,
            shortcut="T",
            checkable=True,
            enabled=True,
            checked=False,
        )

        showVertex = action(
            text=self.tr("显示顶点"),
            slot=self.toggleDrawVertex,
            shortcut="Y",
            checkable=True,
            enabled=True,
            checked=True,
        )
        mosaic = action(
            text=self.tr("添加马赛克"),
            slot=self.mosaicImage,
            shortcut="K",
            enabled=True,
        )
        deMosaic = action(
            text=self.tr("取消马赛克"),
            slot=self.deMosaicImage,
            shortcut=None,
            enabled=False,
        )

        zoom = QtWidgets.QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)

        zoomIn = action(
            text=self.tr("放大"),
            slot=partial(self.board.addZoom, 1.1),
            shortcut="Ctrl+=",
            enabled=True,
        )

        zoomOut = action(
            text=self.tr("缩小"),
            slot=partial(self.board.addZoom, 0.9),
            shortcut="Ctrl+-",
            enabled=True,
        )

        zoomOrg = action(
            text=self.tr("原始大小"),
            slot=partial(self.board.setZoom, 100),
            shortcut="Ctrl+0",
            enabled=True,
        )

        fitWindow = action(
            text=self.tr("&Fit Window"),
            slot=self.setFitWindow,
            shortcut="Ctrl+F",
            checkable=True,
            enabled=False,
        )
        fitWidth = action(
            text=self.tr("Fit &Width"),
            slot=self.setFitWidth,
            shortcut="Ctrl+Shift+F",
            checkable=True,
            enabled=False,
        )

        # Group zoom controls into a list for easier toggling.
        zoomActions = (
            self.zoomWidget,
            zoomIn,
            zoomOut,
            zoomOrg,
            fitWindow,
            fitWidth,
        )

        edit = action(
            text=self.tr("&Edit Label"),
            slot=None,  # self.editLabel,
            shortcut=None,
            enabled=False,
        )

        fill_drawing = action(
            text=self.tr("Fill Drawing Polygon"),
            slot=self.board.canvas.setFillDrawing,
            shortcut=None,
            icon="color",
            tip=self.tr("Fill polygon while drawing"),
            checkable=True,
            enabled=True,
        )
        fill_drawing.trigger()

        copyHere = action(
            text=self.tr("copy here"),
            slot=self.copyShape,
        )

        moveHere = action(
            text=self.tr("move here"),
            slot=self.moveShape,
        )

        self.actions = struct(
            quit=quit, openImg=openImg, openDir=openDir, importLabel=importLabel, importDir=importDir,
            openPrevImg=openPrevImg, openNextImg=openNextImg, recent=recent,

            save=save,  saveAs=saveAs, export=export, export2=export2, exportAll=exportAll, exportSetting=exportSetting,
            saveWithImageData=saveWithImageData,
            check=check, abandon=abandon, normal=normal, checkAll=checkAll, normalAll=normalAll,
            deleteImg=deleteImg, deleteAbandon=deleteAbandon, recovery=recovery, recoveryImg=recoveryImg,

            createPolyMode=createPolyMode, createRectangleMode=createRectangleMode, createCircleMode=createCircleMode,
            createLineMode=createLineMode, createPointMode=createPointMode, createLineStripMode=createLineStripMode,
            editMode=editMode, collectMode=collectMode, maskMode=maskMode,

            duplicate=duplicate, copy=copy, paste=paste, delete=delete,
            removePoint=removePoint, undoLastPoint=undoLastPoint,
            undo=undo, redo=redo, autoTurnEdit=autoTurnEdit,

            hideAll=hideAll, showAll=showAll, showLabelText=showLabelText, showVertex=showVertex,
            mosaic=mosaic, deMosaic=deMosaic,
            zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg, fitWindow=fitWindow, fitWidth=fitWidth,
            tool=(),
            editMenu=(edit, duplicate, copy, paste, delete, None, undo, None, removePoint, None,),
            # menu shown at right click
            menu=(createPolyMode, createRectangleMode, createCircleMode, createLineMode, createPointMode,
                  createLineStripMode, editMode, edit, duplicate, copy, paste, delete, undoLastPoint, undo, removePoint,
                  mosaic, deMosaic),
            edit=edit,
            fill_drawing=fill_drawing,
            zoomActions=zoomActions,
            # TODO 添加关闭文件功能？
            onLoadActive=(
                # close,
                createPolyMode,
                createRectangleMode,
                createCircleMode,
                createLineMode,
                createPointMode,
                createLineStripMode,
                editMode,
            ),
            onShapesPresent=(saveAs, hideAll, showAll),
            copyHere=copyHere, moveHere=moveHere,
        )
        self.actions.tool = (
            openDir,
            openNextImg,
            openPrevImg,
            save,
            deleteImg,
            None,
            createRectangleMode,
            editMode,
            duplicate,
            copy,
            paste,
            delete,
            undo,
            None,
            zoom,
            fitWidth,
        )

    def initMenus(self):
        addActions(
            self.menus.file,
            (
                # self.actions.openImg,
                self.actions.openDir,
                self.actions.importLabel,
                # self.actions.importDir,
                self.actions.openPrevImg,
                self.actions.openNextImg,
                # self.actions.recent,
                self.actions.save,
                # self.actions.saveAs,
                self.actions.export,
                self.actions.export2,
                # self.actions.exportAll,
                # self.actions.exportSetting,
                # self.actions.saveWithImageData,
                None,
                self.actions.check,
                self.actions.abandon,
                self.actions.normal,
                # self.actions.checkAll,
                # self.actions.normalAll,
                self.actions.deleteImg,
                self.actions.deleteAbandon,
                # self.actions.recovery,
                # self.actions.recoveryImg,
                None,
                self.actions.quit,
            ),
        )
        addActions(
            self.menus.edit,
            (
                self.actions.createPolyMode,
                self.actions.createRectangleMode,
                self.actions.createCircleMode,
                self.actions.createLineMode,
                self.actions.createPointMode,
                self.actions.createLineStripMode,
                self.actions.editMode,
                # self.actions.collectMode,
                # self.actions.maskMode,
                self.actions.duplicate,
                self.actions.copy,
                self.actions.paste,
                self.actions.delete,
                self.actions.removePoint,
                self.actions.undoLastPoint,
                self.actions.undo,
                self.actions.redo,
                self.actions.autoTurnEdit,
            )
        )

        addActions(
            self.menus.view,
            (
                self.actions.hideAll,
                self.actions.showAll,
                None,
                self.actions.fill_drawing,
                self.actions.showLabelText,
                self.actions.showVertex,
                self.actions.mosaic,
                self.actions.deMosaic,
                None,
                self.actions.zoomIn,
                self.actions.zoomOut,
                self.actions.zoomOrg,
                None,
                self.actions.fitWindow,
                self.actions.fitWidth,
            )
        )

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            addActions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        # toolbar.setOrientation(Qt.Vertical)
        # toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)

        if actions:
            addActions(toolbar, actions)
        # self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar

    def updateTypeListWidget(self):
        self.listWidget_2.clear()
        for k, v in self.participantMap.items():
            item = QListWidgetItem()
            text = str(k) + ' = ' + str(v)

            item.setData(Qt.UserRole, str(k))
            color = self._get_rgb_by_label(k)
            # item.setBackground(QColor(r,g,b))
            qlabel = QLabel()
            qlabel.setAlignment(Qt.AlignBottom)

            text = '<font color="#{:02x}{:02x}{:02x}">███</font> {}'.format(*color, text)
            qlabel.setText(text)
            item.setSizeHint(qlabel.sizeHint())
            self.listWidget_2.addItem(item)
            self.listWidget_2.setItemWidget(item, qlabel)

    def populateModeActions(self):
        tool, menu = self.actions.tool, self.actions.menu
        self.tools.clear()
        addActions(self.tools, tool)
        self.board.canvas.menus[0].clear()
        addActions(self.board.canvas.menus[0], menu)
        # self.menus.edit.clear()
        # actions = (
        #     self.actions.createPolyMode,
        #     self.actions.createRectangleMode,
        #     self.actions.createCircleMode,
        #     self.actions.createLineMode,
        #     self.actions.createPointMode,
        #     self.actions.createLineStripMode,
        #     self.actions.editMode,
        # )
        # addActions(self.menus.edit, actions + self.actions.editMenu)

    def noShapes(self):
        return not len(self.labelList)

    def setDirty(self):
        # Even if we autosave the file, we keep the ability to undo
        self.actions.undo.setEnabled(self.board.canvas.isShapeRestorable())
        self.actions.redo.setEnabled(self.board.canvas.isShapeRestorable(False))

        # if self._config["auto_save"] or self.actions.saveAuto.isChecked():
        #     label_file = osp.splitext(self.imagePath)[0] + ".json"
        #     if self.output_dir:
        #         label_file_without_path = osp.basename(label_file)
        #         label_file = osp.join(self.output_dir, label_file_without_path)
        #     self.saveLabels(label_file)
        #     return
        self.dirty = True
        self.actions.save.setEnabled(True)
        title = _title
        if self.fileName is not None:
            title = "{} - {}*".format(title, self.fileName)
        self.setWindowTitle(title)

        self.normalFile()

    def setClean(self):
        self.dirty = False
        self.actions.save.setEnabled(False)
        self.actions.createPolyMode.setEnabled(True)
        self.actions.createRectangleMode.setEnabled(True)
        self.actions.createCircleMode.setEnabled(True)
        self.actions.createLineMode.setEnabled(True)
        self.actions.createPointMode.setEnabled(True)
        self.actions.createLineStripMode.setEnabled(True)
        title = _title
        if self.fileName is not None:
            title = "{} - {}".format(title, self.fileName)
        self.setWindowTitle(title)

        # if self.hasLabelFile():
        if self.fileName is not None:
            self.actions.deleteImg.setEnabled(True)
        else:
            self.actions.deleteImg.setEnabled(False)

    def toggleActions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def hasLabelFile(self):
        if self.fileName is None:
            return False

        label_file = self.getLabelFile()
        return osp.exists(label_file)

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.board.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)
    
    def getLabelFile(self):
        if self.fileName.lower().endswith(".json"):
            label_file = self.fileName
        else:
            label_file = osp.splitext(self.fileName)[0] + ".json"

        return label_file

    def saveFile(self):
        """
        ctrl+s 默认保存到cache
        :return:
        """
        if not self.fileName:
            return
        # TODO 另存为功能可借鉴saveFileDialog
        label_dir = osp.join(self.fileDir, self.CACHE, self.LABEL_CACHE)
        label_json_name = osp.splitext(osp.basename(self.fileName))[0] + ".json"
        target_path = osp.join(label_dir, label_json_name)
        self._saveFile(target_path)

    def _saveFile(self, filename):
        if filename and self.saveLabels(filename):
            # self.addRecentFile(filename)
            try:
                if self.arrImageMosaic is not None:
                    # 先转移原图到其他位置
                    origin_img_path = osp.join(self.fileDir, self.CACHE, self.ORIGIN_IMG)
                    if not osp.exists(origin_img_path):
                        os.makedirs(origin_img_path)
                    origin_img_path = osp.join(origin_img_path, osp.basename(self.fileName))
                    shutil.move(self.fileName, origin_img_path)
                    maskimg_path = self.fileName
                    ext = osp.splitext(maskimg_path)[1]
                    status = cv2.imencode(ext, self.arrImageMosaic)[1].tofile(maskimg_path)
            except Exception as e:
                print("_saveFile  ", e)
            self.setClean()

    def exportCheckedLabel(self):
        """
        导出标签，yolo 结果
        :return:
        """
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)

        label_dir = osp.join(self.fileDir, self.CACHE, self.LABEL_CHECK)
        output_dir = osp.join(self.fileDir, self.OUTPUT, self.YOLO_RESULT)

        check_file_list = self.scanAllJsons(label_dir)

        # print(check_file_list)
        cnt = 0

        for check_file in check_file_list:
            try:
                lf = LabelFile(check_file)
            except LabelFileError as e:
                print(e)
                continue
            name = osp.splitext(osp.basename(check_file))[0] + ".cxxxx"  # 加密风险
            tar_path = osp.join(output_dir, name)
            anno_msg = lf.get_data()
            # print(tar_path)
            # ret = self.saveLabelInYolo(data=anno_msg, filename=tar_path)
            ret = save_label_yolo1(data=anno_msg, filename=tar_path, labeldic=self.participantMap)
            if not ret:
                return
            cnt += 1
            if osp.exists(tar_path):
                txt_file = osp.splitext(tar_path)[0] + '.txt'
                os.replace(tar_path, txt_file)
        # 提示成功
        info_text = u"成功导出文件{0}个，请查阅:\n{1}".format(
            cnt, output_dir
        )
        self.infoMessage("导出标签数据", info_text)

    def exportCheckedLabel2(self):
        """
        导出标签，yolo 结果
        :return:
        """
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)

        label_dir = osp.join(self.fileDir, self.CACHE, self.LABEL_CHECK)
        output_dir = osp.join(self.fileDir, self.OUTPUT, self.YOLO_RESULT2)

        check_file_list = self.scanAllJsons(label_dir)

        # print(check_file_list)
        cnt = 0

        for check_file in check_file_list:
            try:
                lf = LabelFile(check_file)
            except LabelFileError as e:
                print(e)
                continue
            name = osp.splitext(osp.basename(check_file))[0] + ".cxxxx"  # 加密风险
            tar_path = osp.join(output_dir, name)
            anno_msg = lf.get_data()
            # print(tar_path)
            # ret = self.saveLabelInYolo(data=anno_msg, filename=tar_path)
            ret = save_label_yolo2(data=anno_msg, filename=tar_path, labeldic=self.participantMap)
            if not ret:
                return
            cnt += 1
            if osp.exists(tar_path):
                txt_file = osp.splitext(tar_path)[0] + '.txt'
                os.replace(tar_path, txt_file)
        # 提示成功
        info_text = u"成功导出文件{0}个，请查阅:\n{1}".format(
            cnt, output_dir
        )
        self.infoMessage("导出标签数据", info_text)

    def checkFile(self):
        """
        check文件
        :return:
        """
        if self.lastFileState is not None and self.lastFileState == FileMsg.checkState:
            # 自动打开下一个
            self.openNextImg()
            return

        if self.dirty:
            self.saveFile()
        label_dir = osp.join(self.fileDir, self.CACHE, self.LABEL_CHECK)
        label_json_name = osp.splitext(osp.basename(self.fileName))[0] + ".json"
        target_path = osp.join(label_dir, label_json_name)
        self._saveFile(target_path)

        fm = self.fileStateDict[osp.basename(self.fileName)]
        print(fm)
        fm.file_state = FileMsg.checkState
        # print(self.imageList)
        currIndex = self.imageList.index(self.fileName)
        print("currIndex=", currIndex)
        item = self.fileListWidget.item(currIndex)
        # item.setIcon(newIcon('done'))
        item.setFileMode(state=fm.file_state)
        item.setData(Qt.UserRole, fm)
        ''' 保存完成labels，更新时间戳、时长保存到文件状态数据  '''
        fm.update_timestamp = self.annoMsg.updateTime
        fm.anno_delay = self.annoMsg.annoDelay

        # 保存self.fileStateDict

        anno_state_file = osp.join(self.fileDir, self.CACHE, self.ANNO_STATE_NAME)
        self.saveAnnoStateFile(anno_state_file)
        self.lastFileState = FileMsg.checkState
        self.reportFileState()

        # 自动打开下一个
        self.openNextImg()

    def abandonFile(self):
        if self.lastFileState is not None and self.lastFileState == FileMsg.abandonState:
            return
        if osp.basename(self.fileName) in self.fileStateDict.keys():
            fm = self.fileStateDict[osp.basename(self.fileName)]
            fm.file_state = FileMsg.abandonState
            currIndex = self.imageList.index(self.fileName)
            item = self.fileListWidget.item(currIndex)
            item.setFileMode(state=fm.file_state)
            item.setData(Qt.UserRole, fm)

            if self.lastFileState is not None and self.lastFileState == FileMsg.checkState:
                # 删除check文件夹内容
                check_path = osp.join(self.fileDir, self.CACHE, self.LABEL_CHECK)
                label_json_name = osp.splitext(osp.basename(self.fileName))[0] + ".json"
                check_path = osp.join(check_path, label_json_name)
                if osp.exists(check_path):
                    os.remove(check_path)

            # 保存self.fileStateDict
            anno_state_file = osp.join(self.fileDir, self.CACHE, self.ANNO_STATE_NAME)
            self.saveAnnoStateFile(anno_state_file)
            self.lastFileState = FileMsg.abandonState
            self.reportFileState()

    def normalFile(self):
        if self.lastFileState is not None and self.lastFileState == FileMsg.normalState:
            return
        if osp.basename(self.fileName) in self.fileStateDict.keys():
            fm = self.fileStateDict[osp.basename(self.fileName)]
            fm.file_state = FileMsg.normalState
            currIndex = self.imageList.index(self.fileName)
            item = self.fileListWidget.item(currIndex)
            item.setFileMode(state=fm.file_state)
            item.setData(Qt.UserRole, fm)
            if self.lastFileState is not None and self.lastFileState == FileMsg.checkState:
                # 删除check文件夹内容
                check_path = osp.join(self.fileDir, self.CACHE, self.LABEL_CHECK)
                label_json_name = osp.splitext(osp.basename(self.fileName))[0] + ".json"
                check_path = osp.join(check_path, label_json_name)
                if osp.exists(check_path):
                    os.remove(check_path)

            # 保存self.fileStateDict
            anno_state_file = osp.join(self.fileDir, self.CACHE, self.ANNO_STATE_NAME)
            self.saveAnnoStateFile(anno_state_file)
            self.lastFileState = FileMsg.normalState
            self.reportFileState()

    def deleteImg(self):
        """
        删除当前图像
        :return:
        """
        deleteInfo = self.deleteImgDialog()
        if deleteInfo != QMessageBox.Yes:
            return
        try:
            if self.fileName and osp.exists(self.fileName):
                self.moveFileToRecyle(osp.basename(self.fileName))

                delete_img_name = self.fileName

                # 列表清除该项
                print(self.imageList)
                idx = self.imageList.index(self.fileName)
                self.imageList.remove(self.fileName)  # 这个要放在前边，否则后边逻辑有bug

                print("idx = ", idx)
                items = self.fileListWidget.selectedItems()
                if not items:
                    return
                item = items[0]
                # print('++++++++777777777===', delete_img_name)
                # item = self.fileListWidget.row(idx)
                # self.fileListWidget.removeItemWidget(item)
                # print(self.fileListWidget.indexFromItem(item).row())
                self._noFileSelectionSlot = True  # 屏蔽文件槽
                delete_row = self.fileListWidget.indexFromItem(item).row()
                self.fileListWidget.takeItem(delete_row)
                self.fileListWidget.update()
                self._noFileSelectionSlot = False

                self.popDeletedImg(delete_img_name)


                if self.fileListWidget.count() > 0:
                    jump_row = min(delete_row, self.fileListWidget.count() - 1)
                    item = self.fileListWidget.item(jump_row)
                    item.setSelected(True)
                    self.fileListWidget.scrollToItem(item)
                    self.fileListWidget.update()
                    self.closeFile()
                    self.fileSelectionChanged()  # 主动触发，读入新文件
                    self.fileDockWidget.setWindowTitle("文件列表 {}/{}".format(jump_row + 1, self.fileListWidget.count()))

                else:
                    # 没有文件了
                    # self.actions.deleteImg.setEnabled(False)
                    self.closeFile()
                    self.importDirImages(self.fileDir)


        except Exception as e:
            print(e)

    def popDeletedImg(self, filename):
        """
        更新字典——移除删除图像信息
        :param filename:
        :return:
        """
        basename = osp.basename(filename)
        if basename in self.labelDict.keys():
            self.labelDict.pop(basename)
        if basename in self.fileStateDict.keys():
            self.fileStateDict.pop(basename)
        if basename in self.fileUpdateTimeDict.keys():
            self.fileUpdateTimeDict.pop(basename)
        if basename in self.fileAnnoDelayDict.keys():
            self.fileAnnoDelayDict.pop(basename)

        # 保存self.fileStateDict
        anno_state_file = osp.join(self.fileDir, self.CACHE, self.ANNO_STATE_NAME)
        if bool(self.fileStateDict):
            self.saveAnnoStateFile(anno_state_file)
        else:
            # 文件删除光
            if osp.exists(anno_state_file):
                os.remove(anno_state_file)

        self.reportFileState()

    def moveFileToRecyle(self, filename):
        """
        将文件挪到回收站
        :param filename:  图像名称，子名称
        :return:
        """
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)

        img_file = osp.join(self.fileDir, filename)
        label_file = osp.splitext(filename)[0] + ".json"

        recycle_path = osp.join(self.fileDir, self.CACHE, self.RECYCLE)
        if not osp.exists(recycle_path):
            os.makedirs(recycle_path)
        print('recycle_path= ',recycle_path)
        # return
        tar_img_path = osp.join(recycle_path, filename)
        if osp.exists(tar_img_path):
            os.remove(tar_img_path)
        # print('img_fil=',img_file)
        # print('tar_img_path=',tar_img_path)
        print(osp.exists(img_file))

        shutil.move(img_file, tar_img_path)  # 剪切走了
        # print('==============')

        # TODO 图像的剪切操作，原图是否还要保留

        # 剪切标签
        labelpath = osp.join(self.fileDir, self.CACHE, self.LABEL_CACHE, label_file)
        tar_label_path = osp.join(recycle_path, label_file)
        if osp.exists(labelpath):
            shutil.move(labelpath, tar_label_path)  # 剪切走了

        # 删除check标签
        if filename in self.fileStateDict.keys() and self.fileStateDict[filename].file_state == FileMsg.checkState:
            check_path = osp.join(self.fileDir, self.CACHE, self.LABEL_CHECK, label_file)
            if osp.exists(check_path):
                os.remove(check_path)


    def queueEvent(self, function):
        QtCore.QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def resetState(self):
        self.labelList.clear()
        self.fileName = None
        self.imagePath = None
        self.imageData = None
        self.labelFile = None
        self.otherData = None

        self.arrImage = None
        self.arrImageMosaic = None

        self.beginTime = None
        self.endTime = None
        self.board.reset()

        self.board.canvas.resetState()
        if self.annoMsg is not None:
            self.annoMsg.reset()
            self.annoMsg = None

        self.actions.undo.setEnabled(self.board.canvas.isShapeRestorable())
        self.actions.redo.setEnabled(self.board.canvas.isShapeRestorable(False))

    def currentItem(self):
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    def undoShapeEdit(self):
        """
        撤回到上一步
        :return:
        """
        self.board.canvas.restoreShape()
        self.labelList.clear()
        self.loadLabels(self.board.canvas.shapes, False)

        self.actions.undo.setEnabled(self.board.canvas.isShapeRestorable())
        self.actions.redo.setEnabled(self.board.canvas.isShapeRestorable(False))

    def redoShapeEdit(self):
        """
        redo
        :return:
        """
        if self.board.canvas.isShapeRestorable(False):
            self.board.canvas.restoreShape(False)
            self.labelList.clear()
            self.loadLabels(self.board.canvas.shapes, False)
            self.actions.undo.setEnabled(self.board.canvas.isShapeRestorable())
            self.actions.redo.setEnabled(self.board.canvas.isShapeRestorable(False))

    def changeLabelAndDisp(self, item):
        """
        双击列表， 修改类别
        :param item:
        :return:
        """
        text = item.data(Qt.UserRole)
        if self.lineEdit_2.isEnabled():
            self.lineEdit_2.setText(text)
        else:
            # 多选状态，将选中的框都刷新为当前的类型
            if len(self.board.canvas.selectedShapes) > 0:
                for shape in self.board.canvas.selectedShapes:
                    shape.label = text
                    item = self.labelList.findItemByShape(shape)
                    tx = self.displayLabelText(shape)
                    item.setText(tx)
                self.board.canvas.storeShapes()
                self.setDirty()
            # 没有选择状态，则当前类别的框选中
            else:
                if self.board.canvas.shapes:
                    s = [shape for shape in self.board.canvas.shapes if shape.label == text]
                    self.board.canvas.selectShapes(s)

    def getLabelAndDisp(self):
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        if self.listWidget_2.currentIndex().row() >= 0:
            pass

        items = self.listWidget_2.selectedItems()
        if not items:
            msg_box = QMessageBox(QMessageBox.Warning, 'Warning',"请在[标签类别]中选中一个类别")
            msg_box.exec_()
            return

        item = items[0]
        text = item.data(Qt.UserRole)
        # self.lineEdit_2.clear()
        self.lineEdit_2.setText(text)

        # print(self.listWidget_2.currentRow())

    def changePlateRegion(self, text):
        if not self.fileName or len(self.board.canvas.shapes) == 0:
            return

        pn = self.lineEdit_3.text()
        if pn:
            if pn[0] in License_Plate_Region:
                pn = text + pn[1:]
            else:
                pn = text + pn
        else:
            pn = text

        self.lineEdit_3.setText(pn)

    def changePlateColor(self, idx):

        # print("changePlateColor")
        # print(data)
        if not self.fileName or len(self.board.canvas.shapes) == 0:
            return

        self.lineEdit_4.setText(str(idx))


    def changeLabelData(self):
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        if self._noLabelEditSlot:
            return

        if not self.board.canvas.editing():
            return

        item = self.currentItem()
        if item is None:
            return
        _text = self.lineEdit_2.text()
        _id = self.spinBox.value()
        _attr = self.spinBox_2.value()

        _plate_num = self.lineEdit_3.text().upper()
        self.lineEdit_3.setText(_plate_num)
        _plate_color = self.lineEdit_4.text()

        shape = item.shape()
        # shape = self.board.canvas.selectedShapes[0]
        shape.label = _text
        shape.id = _id
        shape.attr_value = _attr
        shape.plate_number = _plate_num
        shape.plate_color = int(_plate_color) if _plate_color else 0


        # 更新颜色
        try:
            text = self.displayLabelText(shape)
            item.setText(text)
            # item.setStyleSheet('background-color:#838383;color:white;font:bold 12px;')
        except Exception as e:
            print(sys._getframe().f_lineno," ", e)

        self.board.canvas.storeShapes()
        self.setDirty()

    def fileSelectionChanged(self):
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        if self._noFileSelectionSlot:
            return
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)

        items = self.fileListWidget.selectedItems()
        # aa = [self.fileListWidget.itemFromIndex(i) for i in self.fileListWidget.selectedIndexes()]  # [QListWidgetItem]
        # print(aa==items)  # True

        if not items:
            return
        item = items[0]

        if not self.mayContinue():
            return
        # print('item.text=', str(item.text()))
        # fn = osp.join(self.fileDir, osp.basename(str(item.text())))

        currIndex = self.fileListWidget.indexFromItem(item).row()

        # currIndex = self.imageList.index(str(fn))
        try:
            if currIndex is not None and currIndex < len(self.imageList):
                filename = self.imageList[currIndex]
                if filename:
                    self.loadFile(filename)
        except Exception as e:
            print(sys._getframe().f_lineno, " ",e)

    # React to canvas signals.
    def shapeSelectionChanged(self, selected_shapes):
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        self._noSelectionSlot = True
        for shape in self.board.canvas.selectedShapes:
            shape.selected = False
        self.labelList.clearSelection()
        self.board.canvas.selectedShapes = selected_shapes
        for shape in self.board.canvas.selectedShapes:
            shape.selected = True
            item = self.labelList.findItemByShape(shape)
            self.labelList.selectItem(item)
            self.labelList.scrollToItem(item)
        self._noSelectionSlot = False
        # print('shapeSelectionChanged=', self.labelList.currentIndex().row())

        # 刷新显示标签编辑区
        self._noLabelEditSlot = True
        self.updateLabelEdit()
        self._noLabelEditSlot = False
        n_selected = len(selected_shapes)
        self.actions.delete.setEnabled(n_selected)
        self.actions.duplicate.setEnabled(n_selected)
        self.actions.copy.setEnabled(n_selected)
        self.actions.edit.setEnabled(n_selected == 1)

    def labelSelectionChanged(self):
        if self._noSelectionSlot:
            return
        if self.board.canvas.editing():
            selected_shapes = []
            for item in self.labelList.selectedItems():
                selected_shapes.append(item.shape())
            if selected_shapes:
                self.board.canvas.selectShapes(selected_shapes)
            else:
                self.board.canvas.deSelectShape()

    def shapetypeSelectionChanged(self, item):
        print('shapeSelectionChanged')
        if self.board.canvas.editing():
            if item.text() == "no_draw":
                return
            else:
                self.toggleDrawMode(Canvas.CREATE, createMode=item.text())
        else:
            if item.text() == "no_draw":
                self.toggleDrawMode(Canvas.EDIT)
        # items = self.listWidget_3.selectedItems()
        # if items:
        #     item = items[0]
        #     print(item.text())


    def labelItemChanged(self, item):
        shape = item.shape()
        self.board.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    def labelOrderChanged(self):
        self.setDirty()
        self.board.canvas.loadShapes([item.shape() for item in self.labelList])
        self.board.canvas.orderShapes()

    def updateLabelEdit(self):
        """
        更新标签编辑区
        :return:
        """
        if len(self.board.canvas.selectedShapes) == 1:
            try:
                shape = self.board.canvas.selectedShapes[0]
                self.lineEdit_2.setText(str(shape.label))
                self.spinBox.setValue(int(shape.id))
                self.spinBox_2.setValue(int(shape.attr_value))

                self.lineEdit_3.setText(str(shape.plate_number))
                self.lineEdit_4.setText(str(shape.plate_color))

                # if shape.plate_number and shape.plate_number[0] in License_Plate_Region:
                #     self.comboBox.setCurrentText(shape.plate_number[0])

                if 0 <= shape.plate_color <= 4:
                    self.comboBox_2.setCurrentIndex(shape.plate_color)

                self.editDockWidget.setWindowTitle("标签编辑 No:{}".format(shape.order_no))

                self.lineEdit_2.setEnabled(True)
                self.spinBox.setEnabled(True)
                self.spinBox_2.setEnabled(True)
                self.pushButton.setEnabled(True)
                self.lineEdit_3.setEnabled(True)
                self.lineEdit_4.setEnabled(True)
                self.comboBox.setEnabled(True)
                self.comboBox_2.setEnabled(True)
            except Exception as e:
                print(e)
        else:
            self.lineEdit_2.setText("")
            self.spinBox.setValue(0)
            self.spinBox_2.setValue(0)
            self.editDockWidget.setWindowTitle("标签编辑")
            self.lineEdit_2.setEnabled(False)
            self.spinBox.setEnabled(False)
            self.spinBox_2.setEnabled(False)
            self.pushButton.setEnabled(False)
            self.lineEdit_3.setEnabled(False)
            self.lineEdit_4.setEnabled(False)
            self.comboBox.setEnabled(False)
            self.comboBox_2.setEnabled(False)

    def updateZoom(self, args):
        zoommode, zoomscale, hbar, vbar = args
        self.zoomWidget.setValue(zoomscale)
        if self.fileName:
            self.zoom_values[self.fileName] = (zoommode, zoomscale, hbar, vbar)

    def newShape(self):
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        """Pop-up and give focus to the label editor.

        position MUST be in global coordinates.
        """
        # TODO lablename 可以取当前定的
        text = "car"
        items = self.listWidget_2.selectedItems()
        if items:
            item = items[0]
            text = item.data(Qt.UserRole)

        # TODO 是否自动弹出编辑框
        flags = {}
        self.labelList.clearSelection()
        shape = self.board.canvas.setLastLabel(text, flags)

        shape.imgWidth = self.annoMsg.imageWidth
        shape.imgHeight = self.annoMsg.imageHeight
        self.addLabel(shape)

        self.actions.editMode.setEnabled(True)
        self.actions.undoLastPoint.setEnabled(False)
        self.actions.undo.setEnabled(True)

        self.setDirty()

        # 编辑模式自动恢复
        if self.actions.autoTurnEdit.isChecked():
            self.setEditMode()

        return
        # items = self.uniqLabelList.selectedItems()
        # text = None
        # if items:
        #     text = items[0].data(Qt.UserRole)
        # flags = {}
        # group_id = None
        # if self._config["display_label_popup"] or not text:
        #     previous_text = self.labelDialog.edit.text()
        #     text, flags, group_id = self.labelDialog.popUp(text)
        #     if not text:
        #         self.labelDialog.edit.setText(previous_text)
        #
        # if text and not self.validateLabel(text):
        #     self.errorMessage(
        #         self.tr("Invalid label"),
        #         self.tr("Invalid label '{}' with validation type '{}'").format(
        #             text, self._config["validate_label"]
        #         ),
        #     )
        #     text = ""
        # if text:
        #     self.labelList.clearSelection()
        #     shape = self.board.canvas.setLastLabel(text, flags)
        #     shape.group_id = group_id
        #     self.addLabel(shape)
        #     self.actions.editMode.setEnabled(True)
        #     self.actions.undoLastPoint.setEnabled(False)
        #     self.actions.undo.setEnabled(True)
        #     self.setDirty()
        # else:
        #     self.board.canvas.undoLastLine()
        #     self.board.canvas.shapesBackups.pop()

    def updateLabelPoints(self):
        """
        框顶点或整体移动== points变更,触发函数
        :return:
        """
        # print("updateLabelPoints")

        # TODO 更新列表数据 - 如果显示point

        self.setDirty()


    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.board.setFitWindow(value)


    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.board.setFitWidth(value)

    def resizeEvent(self, event):
        super(AppEntry, self).resizeEvent(event)

    def adjustScale(self, initial=False):

        self.board.adjustScale(initial)



    def mosaicImage(self):
        """
        给图片打码，适合定向打码
        :return:
        """
        if self.arrImage is None:
            return
        if not self.board.canvas.selectedShapes:
            return

        rects = []
        for shape in self.board.canvas.selectedShapes:
            if shape.shape_type == "rectangle":
                rects.append(shape.boundingRect())
        if len(rects) == 0:
            return

        try:
            boxs = [
                [int(rect.topLeft().x()), int(rect.topLeft().y()), int(rect.width()), int(rect.height())]
                for rect in rects
            ]
            t1 = time.time()
            if self.arrImageMosaic is None:
                array_img = self.arrImage.copy()  # 深拷贝，不改变原数据
            else:
                array_img = self.arrImageMosaic.copy()
            for box in boxs:
                x, y, w, h = box
                do_mosaic(array_img, x, y, w, h, neighbor=11)
            t2 = time.time()
            # 显示刷新
            height, width, depth = array_img.shape
            self.arrImageMosaic = array_img.copy()

            array_img = cv2.cvtColor(array_img, cv2.COLOR_BGR2RGB)
            image = QImage(array_img.data, width, height, width * depth, QImage.Format_RGB888)
            if image.isNull():
                return False
            self.image = image
            self.pixmap = QPixmap.fromImage(image)
            self.board.canvas.loadPixmap(self.pixmap, clear_shapes=False)
            self.actions.deMosaic.setEnabled(True)
            self.setDirty()

            t3 = time.time()

            # print("时间 打码 ", t2-t1)
            #             # print("显示时间 ", t3-t2)

        except Exception as e:
            print(e)

    def deMosaicImage(self):
        """
        将本次打码操作全部撤销，恢复原图
        :return:
        """
        if self.arrImage is None or self.arrImageMosaic is None:
            return
        self.board.canvas.deSelectShape()
        height, width, depth = self.arrImage.shape
        cvimg = cv2.cvtColor(self.arrImage, cv2.COLOR_BGR2RGB)
        image = QImage(cvimg.data, width, height, width * depth, QImage.Format_RGB888)
        if image.isNull():
            return False

        self.arrImageMosaic = None

        self.image = image
        self.pixmap = QPixmap.fromImage(image)
        self.board.canvas.loadPixmap(self.pixmap, clear_shapes=False)
        self.actions.deMosaic.setEnabled(False)
        self.setDirty()

    def enableSaveImageWithData(self, enabled):
        # self._config["store_data"] = enabled
        print("enableSaveImageWithData = ", enabled)
        self.actions.saveWithImageData.setChecked(enabled)

    def toggleDrawingSensitive(self, drawing=True):
        """Toggle drawing sensitive.

        In the middle of drawing, toggling between modes should be disabled.
        """
        self.actions.editMode.setEnabled(not drawing)
        self.actions.undoLastPoint.setEnabled(drawing)
        self.actions.undo.setEnabled(not drawing)
        self.actions.delete.setEnabled(not drawing)

    def toggleDrawMode(self, mode=Canvas.EDIT, createMode="polygon"):
        self.board.canvas.setMode(mode)
        self.board.canvas.createMode = createMode
        if mode == Canvas.EDIT:
            self.actions.createPolyMode.setEnabled(True)
            self.actions.createRectangleMode.setEnabled(True)
            self.actions.createCircleMode.setEnabled(True)
            self.actions.createLineMode.setEnabled(True)
            self.actions.createPointMode.setEnabled(True)
            self.actions.createLineStripMode.setEnabled(True)

            self.actions.maskMode.setEnabled(True)
            self.actions.editMode.setEnabled(False)


        elif mode == Canvas.CREATE:
            if createMode == "polygon":
                self.actions.createPolyMode.setEnabled(False)
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createCircleMode.setEnabled(True)
                self.actions.createLineMode.setEnabled(True)
                self.actions.createPointMode.setEnabled(True)
                self.actions.createLineStripMode.setEnabled(True)
            elif createMode == "rectangle":
                self.actions.createPolyMode.setEnabled(True)
                self.actions.createRectangleMode.setEnabled(False)
                self.actions.createCircleMode.setEnabled(True)
                self.actions.createLineMode.setEnabled(True)
                self.actions.createPointMode.setEnabled(True)
                self.actions.createLineStripMode.setEnabled(True)
            elif createMode == "line":
                self.actions.createPolyMode.setEnabled(True)
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createCircleMode.setEnabled(True)
                self.actions.createLineMode.setEnabled(False)
                self.actions.createPointMode.setEnabled(True)
                self.actions.createLineStripMode.setEnabled(True)
            elif createMode == "point":
                self.actions.createPolyMode.setEnabled(True)
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createCircleMode.setEnabled(True)
                self.actions.createLineMode.setEnabled(True)
                self.actions.createPointMode.setEnabled(False)
                self.actions.createLineStripMode.setEnabled(True)
            elif createMode == "circle":
                self.actions.createPolyMode.setEnabled(True)
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createCircleMode.setEnabled(False)
                self.actions.createLineMode.setEnabled(True)
                self.actions.createPointMode.setEnabled(True)
                self.actions.createLineStripMode.setEnabled(True)
            elif createMode == "linestrip":
                self.actions.createPolyMode.setEnabled(True)
                self.actions.createRectangleMode.setEnabled(True)
                self.actions.createCircleMode.setEnabled(True)
                self.actions.createLineMode.setEnabled(True)
                self.actions.createPointMode.setEnabled(True)
                self.actions.createLineStripMode.setEnabled(False)
            else:
                raise ValueError("Unsupported createMode: %s" % createMode)

            self.actions.maskMode.setEnabled(False)  # 只有编辑模式可以切换到马赛克模式
            self.actions.editMode.setEnabled(True)

        elif mode == Canvas.MOSAIC:
            self.actions.maskMode.setEnabled(False)
            self.actions.editMode.setEnabled(True)

    def setEditMode(self):
        self.toggleDrawMode(Canvas.EDIT)
        self.board.canvas.update()

    def setMosaicMode(self):
        self.toggleDrawMode(Canvas.MOSAIC)
        self.board.canvas.update()
    
    def updateFileMenu(self):
        current = self.fileName

        # def exists(filename):
        #     return osp.exists(str(filename))
        #
        # menu = self.menus.recentFiles
        # menu.clear()
        # files = [f for f in self.recentFiles if f != current and exists(f)]
        # for i, f in enumerate(files):
        #     icon = newIcon("labels")
        #     action = QtWidgets.QAction(
        #         icon, "&%d %s" % (i + 1, QtCore.QFileInfo(f).fileName()), self
        #     )
        #     action.triggered.connect(partial(self.loadRecent, f))
        #     menu.addAction(action)

    def showPosition(self, px, py):
        """
        显示图像坐标
        :param px:
        :param py:
        :return:
        """
        self.labelCoordinates.setText("X:{},Y:{}".format(round(px, 1), round(py, 1)))


    def popLabelListMenu(self, point):
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def deleteImgDialog(self):
        yes, cancel = QMessageBox.Yes, QMessageBox.Cancel
        msg = u'图像将被转移至recycle(可恢复),请确认'
        return QMessageBox.warning(self, u'Attention', msg, yes | cancel)

    def mayContinue(self):
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        if not self.dirty:
            return True
        mb = QtWidgets.QMessageBox
        msg = self.tr('Save annotations to "{}" before closing?').format(
            self.fileName
        )
        answer = mb.question(
            self,
            self.tr("Save annotations?"),
            msg,
            mb.Save | mb.Discard | mb.Cancel,
            mb.Save,
        )
        if answer == mb.Discard:
            return True
        elif answer == mb.Save:
            self.saveFile()
            return True
        else:  # answer == mb.Cancel
            return False

    def displayLabelText(self, shape):
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        text = "{0}-{1}| id:{2} | attr:{3} col:{4} lic:{5}".format(
            shape.order_no,
            shape.label,
            shape.id,
            shape.attr_value,
            shape.plate_color,
            shape.plate_number
        )
        # █ □●◇★ ￭ ◢◣◤◥○▲▼∠
        tag = '●'
        if shape.shape_type == "rectangle":
            tag = "█"
        elif shape.shape_type == "point":
            tag = "★"
        elif shape.shape_type == "circle":
            tag = "●"
        elif shape.shape_type == "line":
            tag = "▍"
        elif shape.shape_type == "linestrip":
            tag = "▲"
        elif shape.shape_type == "polygon":
            tag = "◆"

        self._update_shape_color(shape)
        # '{} <font color="#{:02x}{:02x}{:02x}">{}</font>  '.format(
        #     text, *shape.fill_color.getRgb()[:3], tag

        # text = '{} <font color="#{:02x}{:02x}{:02x}" face="黑体" size=15>{}</font>  '.format(
        #         text, *shape.fill_color.getRgb()[:3], tag)

        # print("rgb=", r, g,b)
        # print(*shape.fill_color.getRgb()[:3])

        text = '{} <font color="#{:02x}{:02x}{:02x}">{}</font>  '.format(
            text, *shape.fill_color.getRgb()[:3], tag)

        # item.setStyleSheet('background-color:#838383;color:white;font:bold 12px;')

        return text


    def addLabel(self, shape):
        """
        添加标签
        :param shape:
        :return:
        """
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)

        label_list_item = LabelListWidgetItem(shape=shape)
        text = self.displayLabelText(shape)
        label_list_item.setText(text)
        # font = QFont()
        # font.setPointSize(25)
        # label_list_item.setFont(font)

        self.labelList.addItem(label_list_item)

        for action in self.actions.onShapesPresent:
            action.setEnabled(True)

    def _update_shape_color(self, shape):
        r, g, b = self._get_rgb_by_label(shape.label)
        shape.line_color = QtGui.QColor(r, g, b)
        shape.vertex_fill_color = QtGui.QColor(r, g, b)
        shape.hvertex_fill_color = QtGui.QColor(255, 255, 255)
        shape.fill_color = QtGui.QColor(r, g, b, 75)  # 悬浮填充颜色
        shape.select_line_color = QtGui.QColor(255, 255, 255)
        shape.select_fill_color = QtGui.QColor(r, g, b, 100)  # 选中填充
        shape.updateModeDict()

    def _get_rgb_by_label(self, label):
        # if self._config["shape_color"] == "auto":
        #     item = self.uniqLabelList.findItemsByLabel(label)[0]
        #     label_id = self.uniqLabelList.indexFromItem(item).row() + 1
        #     label_id += self._config["shift_auto_shape_color"]
        #     return LABEL_COLORMAP[label_id % len(LABEL_COLORMAP)]
        # elif (
        #     self._config["shape_color"] == "manual"
        #     and self._config["label_colors"]
        #     and label in self._config["label_colors"]
        # ):
        #     return self._config["label_colors"][label]
        # elif self._config["default_shape_color"]:
        #     return self._config["default_shape_color"]
        SEED = 61
        type_list = list(self.participantMap.keys())
        random.seed(SEED)
        random.shuffle(type_list)

        step = int(len(LABEL_COLORMAP2) / len(type_list))
        if label in type_list:
            label_id = type_list.index(label)
            # return LABEL_COLORMAP[label_id % len(LABEL_COLORMAP)]

            color = LABEL_COLORMAP2[step*label_id]
            return color

        return (0, 240, 230)

    def togglePolygons(self, value):
        if self.noShapes():
            return
        for item in self.labelList:
            item.setCheckState(Qt.Checked if value else Qt.Unchecked)

    def toggleDrawText(self,value):
        """
        是否显示字体
        :param value:
        :return:
        """
        # print('toggleDrawText',value)
        Shape.identified = value
        self.board.canvas.update()

    def toggleDrawVertex(self, value):
        """
        是否显示顶点
        :param value:
        :return:
        """
        # print('toggleDrawText',value)
        Shape.vertexed = value
        self.board.canvas.update()

    def remLabels(self, shapes):
        for shape in shapes:
            item = self.labelList.findItemByShape(shape)
            self.labelList.removeItem(item)

    def refreshLabels(self, shapes):
        try:
            for shape in shapes:
                item = self.labelList.findItemByShape(shape)
                text = self.displayLabelText(shape)
                item.setText(text)
        except Exception as e:
            print("refreshLabels  ", e)

    def loadShapes(self, shapes, replace=True):
        """
        :param shapes:  [Shape(),]
        :param replace:
        :return:
        """
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        self._noSelectionSlot = True
        for shape in shapes:
            self.addLabel(shape)
        self.labelList.clearSelection()
        self._noSelectionSlot = False
        self.board.canvas.loadShapes(shapes, replace=replace)
        self.refreshLabels(shapes)

    def loadLabels(self, shapes, canv=True):
        # print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        """

        :param shapes:
        :param canv: True 标签加载到画布里，False 不加载到画布，只更新列表
        :return:
        """
        try:
            if canv:
                self.loadShapes(shapes)
            else:
                self._noSelectionSlot = True
                for shape in shapes:
                    self.addLabel(shape)
                self.labelList.clearSelection()
                self._noSelectionSlot = False
                self.refreshLabels(shapes)

        except Exception as e:
            print(e)

    def loadFile(self, filename=None):
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name, ' ', \
              sys._getframe().f_back.f_code.co_name, ' ', sys._getframe().f_back.f_back.f_code.co_name)

        # 预防重复进入,
        # TODO 有点bug ，不能上下键，鼠标持续拉不行
        if filename in self.imageList and (
            self.fileListWidget.currentRow() != self.imageList.index(filename)
        ):
            print('loadFile=', self.fileListWidget.currentRow(),'  ', self.imageList.index(filename))
            self.fileListWidget.setCurrentRow(self.imageList.index(filename))
            self.fileListWidget.update()
            # index = self.mImgList.index(unicodeFilePath)
            # fileWidgetItem = self.fileListWidget.item(index)
            # fileWidgetItem.setSelected(True)

            return

        idx = self.imageList.index(filename)
        self.fileDockWidget.setWindowTitle("文件列表 {}/{}".format(idx + 1, len(self.imageList)))
        self.resetState()

        # 先不让图像控件使能
        # self.zoom_values[self.fileName]
        h_sbar = self.board.scrollBars[Qt.Horizontal].value()
        v_sbar = self.board.scrollBars[Qt.Vertical].value()
        zoomscale = self.board.getZoom()

        # TODO 点击上一个下一个时候，这块enable 再打开，会让控件自动居中，刷新bars，不知道什么原理
        self.board.canvas.setEnabled(False)
        # print("h3,v3 = ", self.scrollBars[Qt.Horizontal].value(), self.scrollBars[Qt.Vertical].value())
        # 第一次进入 给的空的话，进入设置的文件目录
        # if filename is None:
        #     filename = self.settings.value("filename", "")
        filename = str(filename)
        if not QtCore.QFile.exists(filename):
            # print('filename=', filename)
            self.errorMessage(self.tr("Error opening file"), self.tr("No such file: <b>%s</b>") % filename)
            return False

        self.status(str(self.tr("Loading %s...")) % osp.basename(str(filename)))
        self.beginTime = time.time()

        #  -----------------读图像--------------------

        t1 = time.time()

        self.arrImage = cv2_load(filename)
        qimg = array2qimage(self.arrImage)
        if qimg.isNull():
            self.errorMessage(u'Error opening file',
                              u"<p>Make sure <i>%s</i> is a valid image file." % filename)
            self.status("Error reading %s" % filename)
            return False

        self.status("Loaded %s" % os.path.basename(filename))
        self.image = qimg
        self.pixmap = qimage2qpixmap(qimg)
        self.board.loadImage(qimg)
        self.fileName = filename
        t2 = time.time()

        # 另外读取图像方法
        # self.imageData = LabelFile.load_image_file(filename)
        # if self.imageData:
        #     self.imagePath = filename
        # self.image = QtGui.QImage.fromData(self.imageData)
        # self.pixmap = QPixmap.fromImage(image)
        # self.board.canvas.loadPixmap(self.pixmap)

        # -----------------读标签--------------------
        # 默认访问 ./cache/label_cache/
        label_dir = osp.join(self.fileDir, self.CACHE, self.LABEL_CACHE)
        label_json_name = osp.splitext(osp.basename(filename))[0] + ".json"
        label_file = osp.join(label_dir, label_json_name)

        # 如果设置了其他地方文件夹，则访问那里的，就不默认访问
        # label_file = osp.splitext(filename)[0] + ".json"
        # if self.output_dir:
        #     print('output_dir=', self.output_dir)
        #     label_file_without_path = osp.basename(label_file)
        #     label_file = osp.join(self.output_dir, label_file_without_path)

        if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(label_file):
            try:
                self.labelFile = LabelFile(label_file, self.fileName)
            except LabelFileError as e:
                self.errorMessage(
                    self.tr("Error opening file"),
                    self.tr(
                        "<p><b>%s</b></p>"
                        "<p>Make sure <i>%s</i> is a valid label file."
                    )
                    % (e, label_file),
                )
                self.status(self.tr("Error reading %s") % label_file)
                return False

            self.annoMsg = self.labelFile.get_data()

            self.fileUpdateTimeDict[osp.basename(filename)] = self.annoMsg.updateTime
            self.fileAnnoDelayDict[osp.basename(filename)] = self.annoMsg.annoDelay
            self.labelShapes = self.annoMsg.shapes  # 标注信息框列表
            # print("self.annoMsg.shapes=",self.annoMsg.shapes)

        else:
            self.labelFile = None
            #  只有算法文件的话
            # print('=====================')
            # print(self.labelDict.keys())

            # print(osp.basename(filename),"  ", osp.basename(filename) in self.labelDict.keys())
            self.labelShapes = self.labelDict.get(osp.basename(filename), [])
            self.annoMsg = AnnoMsg()
            self.annoMsg.shapes = self.labelShapes

        t3 = time.time()

        if self.annoMsg.imagePath != osp.basename(self.fileName):
            self.annoMsg.imagePath = osp.basename(self.fileName)

        if self.image and not self.image.isNull():
            # TODO提示 按照批量预处理吧
            # if self.annoMsg.imageHeight != self.image.height() or \
            #         self.annoMsg.imageWidth != self.image.width():
            #     self.infoMessage("image scale", "检测到标签记录图像尺寸有误，已更新数据")
            #     self.setDirty()
            self.annoMsg.imageHeight = self.image.height()
            self.annoMsg.imageWidth = self.image.width()
            # TODO imageData 是当前图片转base64
            # base64_str = cv2.imencode(".png", self.arrImage)[1].tostring()
            # print("base64_str1 = ", base64_str)
            # base64_str = base64.b64encode(base64_str)
            # print("base64_str2 = ", base64_str)

        self.labelDict[osp.basename(filename)] = self.labelShapes
        self.loadLabels(self.labelShapes)
        t4 = time.time()

        # --------------状态-----------
        if osp.basename(filename) not in self.fileStateDict.keys():
            fm = FileMsg()
            fm.file_name = osp.basename(filename)
            fm.file_state = FileMsg.normalState
            fm.img_state = FileMsg.originImg
            self.fileStateDict[osp.basename(filename)] = fm
            fm.update_timestamp = self.annoMsg.updateTime
            fm.anno_delay = self.annoMsg.annoDelay
            # print(self.fileStateDict)

        self.lastFileState = self.fileStateDict[osp.basename(filename)].file_state
        try:
            self.label_4.setText("标注用时:{} s".format(round(self.annoMsg.annoDelay, 1)))
            self.label_5.setText("更新时间:{}".format(self.annoMsg.updateTime))
        except Exception as e:
            print(e)



        # print("tu =", t2 - t1)
        # print("bq =", t3 - t2)
        # print("jiazia =", t4 - t3)

        # if self._config["keep_prev"]:
        #     prev_shapes = self.board.canvas.shapes
        # self.board.canvas.loadPixmap(QtGui.QPixmap.fromImage(image))
        # flags = {k: False for k in self._config["flags"] or []}

        # if self.labelFile:
        #     self.loadLabels(self.labelFile.shapes)
        #     if self.labelFile.flags is not None:
        #         flags.update(self.labelFile.flags)
        # self.loadFlags(flags)
        # if self._config["keep_prev"] and self.noShapes():
        #     self.loadShapes(prev_shapes, replace=False)
        #     self.setDirty()
        # else:
        #     self.setClean()

        self.setClean()
        self.board.canvas.setEnabled(True)

        # 希望保持之前的缩放状态策略
        if not bool(self.zoom_values):
            '''first in'''
            self.adjustScale(initial=True)
        else:
            self.board.setZoom(zoomscale)
            self.board.setScroll(Qt.Horizontal, h_sbar)
            self.board.setScroll(Qt.Vertical, v_sbar)


        self.board.paintCanvas()
        # TODO 亮度对比对BrightnessContrastDialog

        # TODO 添加至最新文件self.addRecentFile(self.fileName)
        self.updateLabelEdit()  # 刚加载入文件，先让控件封闭
        self.toggleActions(True)
        self.board.canvas.setFocus()
        self.status(str(self.tr("Loaded %s")) % osp.basename(str(filename)))
        return True

    def saveLabels(self, filename):
        """
        保存到json
        :param filename:
        :return:
        """
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        print('saveLabels filename=', filename)
        lf = LabelFile()
        self.endTime = time.time()
        if self.annoMsg is None:
            self.annoMsg = AnnoMsg()
        self.annoMsg.shapes = self.board.canvas.shapes
        self.annoMsg.version = __version__
        self.annoMsg.updateTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.annoMsg.annoDelay = round(self.endTime - self.beginTime, 1)
        self.annoMsg.datasetName = "test"
        self.label_4.setText("标注用时:{} s".format(self.annoMsg.annoDelay))
        self.label_5.setText("更新时间:{}".format(self.annoMsg.updateTime))
        lf.set_data(self.annoMsg)

        try:
            if osp.dirname(filename) and not osp.exists(osp.dirname(filename)):
                os.makedirs(osp.dirname(filename))

            lf.save(filename)
            # self.labelFile = lf
            # items = self.fileListWidget.findItems(
            #     self.imagePath, Qt.MatchExactly
            # )
            # if len(items) > 0:
            #     if len(items) != 1:
            #         raise RuntimeError("There are duplicate files.")
            #     items[0].setCheckState(Qt.Checked)
            # disable allows next and previous image to proceed
            # self.fileName = filename
            return True
        except LabelFileError as e:
            self.errorMessage(
                self.tr("Error saving label data"), self.tr("<b>%s</b>") % e
            )
            return False

    def openPrevImg(self, _value=False):
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        # keep_prev = self._config["keep_prev"]
        # if QtWidgets.QApplication.keyboardModifiers() == (
        #     Qt.ControlModifier | Qt.ShiftModifier
        # ):
        #     self._config["keep_prev"] = True

        if not self.mayContinue():
            return

        if len(self.imageList) <= 0:
            return

        if self.fileName is None:
            return

        currIndex = self.imageList.index(self.fileName)
        if currIndex - 1 >= 0:
            filename = self.imageList[currIndex - 1]
            self.fileName = filename
            self.loadFile(self.fileName)

    def openNextImg(self, _value=False, load=True):
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        # keep_prev = self._config["keep_prev"]
        # if QtWidgets.QApplication.keyboardModifiers() == (
        #     Qt.ControlModifier | Qt.ShiftModifier
        # ):
        #     self._config["keep_prev"] = True

        if not self.mayContinue():
            return

        if len(self.imageList) <= 0:
            return

        filename = None
        if self.fileName is None:
            filename = self.imageList[0]
        else:
            currIndex = self.imageList.index(self.fileName)
            if currIndex + 1 < len(self.imageList):
                filename = self.imageList[currIndex + 1]
            else:
                filename = self.imageList[-1]
        self.fileName = filename
        if self.fileName and load:
            self.loadFile(self.fileName)

    def errorMessage(self, title, message):
        return QtWidgets.QMessageBox.critical(
            self, title, "<p><b>%s</b></p>%s" % (title, message)
        )

    def infoMessage(self, title, message):
        return QtWidgets.QMessageBox.information(
            self, title, "<p><b>%s</b></p>%s" % (title, message)
        )

    def currentPath(self):
        return osp.dirname(str(self.filename)) if self.filename else "."

    def removeSelectedPoint(self):
        """
        删除选中的点
        :return:
        """
        print('removeSelectedPoint')
        self.board.canvas.removeSelectedPoint()
        self.board.canvas.update()

    def duplicateSelectedShape(self):
        """
        拷贝 ctrl+d
        :return:
        """
        added_shapes = self.board.canvas.duplicateSelectedShapes()
        self.labelList.clearSelection()
        for shape in added_shapes:
            self.addLabel(shape)
        self.refreshLabels(self.board.canvas.shapes)  # 刷新标签序号和列表显示
        self.setSelectShape(added_shapes)
        self.setDirty()

    def pasteSelectedShape(self):
        """
        粘贴 ctrl+v
        :return:
        """
        # TODO 是否应校验一下尺寸
        if self._copied_shapes is None:
            return
        shapes = copy.deepcopy(self._copied_shapes)
        for shape in shapes:
            shape.imgWidth = self.annoMsg.imageWidth
            shape.imgHeight = self.annoMsg.imageHeight

        for shape in self.board.canvas.shapes:
            shape.selected = False
        self.loadShapes(shapes, replace=False)
        self.setSelectShape(shapes)
        self.setDirty()

    def setSelectShape(self, shapes):
        """
        框为选中状态 ，用于粘贴
        :param shapes:
        :return:
        """
        for shape in shapes:
            shape.selected = True
            self.board.canvas.selectedShapes = shapes
            self.board.canvas.selectionChanged.emit(self.board.canvas.selectedShapes)

    def copySelectedShape(self):
        """
        复制 ctrl+c
        :return:
        """
        self._copied_shapes = [s.copy() for s in self.board.canvas.selectedShapes]
        self.actions.paste.setEnabled(len(self._copied_shapes) > 0)

    def deleteSelectedShape(self):
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        # yes, no = QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        # msg = self.tr(
        #     "You are about to permanently delete {} polygons, "
        #     "proceed anyway?"
        # ).format(len(self.board.canvas.selectedShapes))
        # if yes == QtWidgets.QMessageBox.warning(
        #         self, self.tr("Attention"), msg, yes | no, yes
        # ):
        #     self.remLabels(self.board.canvas.deleteSelected())
        #     self.refreshLabels(self.board.canvas.shapes)
        #     self.setDirty()
        #     if self.noShapes():
        #         for action in self.actions.onShapesPresent:
        #             action.setEnabled(False)

        self.remLabels(self.board.canvas.deleteSelected())
        self.refreshLabels(self.board.canvas.shapes)
        self.setDirty()
        if self.noShapes():
            for action in self.actions.onShapesPresent:
                action.setEnabled(False)

    def copyShape(self):
        """
        右键移动，复制
        :return:
        """
        pastedShapes = []
        self.board.canvas.endMove(copy=True)
        for shape in self.board.canvas.selectedShapes:
            self.addLabel(shape)
            pastedShapes.append(shape)
        self.labelList.clearSelection()

        if pastedShapes:
            self.setSelectShape(pastedShapes)
        self.setDirty()
        del pastedShapes

    def moveShape(self):
        """
        右键移动，移动
        :return:
        """
        self.board.canvas.endMove(copy=False)
        self.setDirty()

    def reportFileState(self):
        """
        统计文件信息
        :return:
        """
        check_cnt = 0
        abandon_cnt = 0
        normal_cnt = 0
        for k, v in self.fileStateDict.items():
            if v.file_state == FileMsg.checkState:
                check_cnt += 1
            elif v.file_state == FileMsg.abandonState:
                abandon_cnt += 1

        all_cnt = len(self.imageList)
        if all_cnt > 0:
            normal_cnt = all_cnt - check_cnt - abandon_cnt

            self.label_2.setText("已完成：{}, {}%".format(check_cnt, round((check_cnt/all_cnt)*100, 1)))
            self.label_3.setText("待丢弃：{}, {}%".format(abandon_cnt, round((abandon_cnt / all_cnt) * 100, 1)))
        else:
            self.label_2.setText("已完成：-")
            self.label_3.setText("待丢弃：-")
            self.label_4.setText("标注用时： -")
            self.label_5.setText("完成时间：-")

    def openDirDialog(self, _value=False, dirpath=None):
        if not self.mayContinue():
            return

        defaultOpenDirPath = dirpath if dirpath else "."
        if self.lastOpenDir and osp.exists(self.lastOpenDir):
            defaultOpenDirPath = self.lastOpenDir
        else:
            defaultOpenDirPath = (
                osp.dirname(self.fileName) if self.fileName else "."
            )

        targetDirPath = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Open Directory") % _title,
                defaultOpenDirPath,
                QtWidgets.QFileDialog.ShowDirsOnly
                | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )
        print('targetDirPath=', targetDirPath)
        self.importDirImages(targetDirPath)

    def importDirImages(self, dirpath, pattern=None, load=True):
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        self.actions.openNextImg.setEnabled(True)
        self.actions.openPrevImg.setEnabled(True)

        if not self.mayContinue() or not dirpath:
            return

        if not osp.exists(dirpath):
            return

        # TODO 数据初始化操作
        self.lastOpenDir = dirpath
        self.fileName = None
        self.fileListWidget.clear()
        self.imageList = self.scanAllImages(dirpath)
        self.fileDir = dirpath

        self.fileStateDict = {}
        self.fileDockWidget.setWindowTitle("文件列表")
        # print('imageList=', self.imageList)
        self.zoom_values = {}

        # 读取算法标注文件
        auto_label_folder = osp.join(self.fileDir, self.CACHE)
        self.labelDict = self.loadAutoLabelFile(auto_label_folder)
        # print('self.labelDict.keys = ', list(self.labelDict.keys()))

        # cache/anno_state.json ,进行过保存操作，就会更新该文件
        anno_state_file = osp.join(self.fileDir, self.CACHE, self.ANNO_STATE_NAME)
        self.fileStateDict = self.loadAnnoStateFile(anno_state_file)

        # 查看当前文件里是否有映射文件，可以导入
        backup_type = self.participantMap
        typefilepath = osp.join(dirpath, "class.json")
        self.participantMap = self.loadTypeMap(typefilepath)  # 交通参与者映射
        if not bool(self.participantMap):
            self.participantMap = backup_type
        else:
            self.updateTypeListWidget()

        self.reportFileState()
        # print(self.fileStateDict)

        # for img_name in [osp.basename(img) for img in self.imageList]:
        #     if img_name not in self.fileStateDict.keys():
        #         self.fileStateDict[img_name] = FileMsg()

        # print(self.imageList)
        for filename in self.imageList:
            if pattern and pattern not in filename:
                continue
            # 查看同目录下是否有标签json文件
            label_file = osp.splitext(filename)[0] + ".json"
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)
            # item = QListWidgetItem(filename)
            # print('filename=', filename)
            # print(osp.basename(filename))
            f_state = self.fileStateDict.get(osp.basename(filename), None)
            # print('f_state=',f_state)
            item = FileListWidgetItem(text=osp.basename(filename), file=f_state)
            # item = QListWidgetItem()
            # item.setText(osp.basename(filename))
            # item.setData(Qt.UserRole, 0)
            # item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            # item.setIcon(QIcon(":/done"))
            if f_state is None:
                item.setFileMode()
            else:
                # print(osp.basename(filename))
                # print('  ',f_state.file_state)
                item.setFileMode(state=f_state.file_state)


            # if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(
            #     label_file
            # ):
            #     item.setCheckState(Qt.Checked)
            # else:
            #     item.setCheckState(Qt.Unchecked)
            self.fileListWidget.addItem(item)
        self.openNextImg(load=load)
        self.setClean()

    def scanAllImages(self, folderPath):
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]

        images = []
        # print(os.listdir(folderPath))
        for file in os.listdir(folderPath):
            if file.lower().endswith(tuple(extensions)):
                relativePath = osp.join(folderPath, file)
                images.append(relativePath)

        # for root, dirs, files in os.walk(folderPath):
        #     for file in files:
        #         if file.lower().endswith(tuple(extensions)):
        #             relativePath = osp.join(root, file)
        #             images.append(relativePath)
        # images.sort(key=lambda x: x.lower())
        natural_sort(images, key=lambda x: x.lower())
        print(images)
        return images

    def scanAllJsons(self, folderPath):
        """
        扫描当前文件夹算法文件，autolabel xxx.json
        :param folderPath:
        :return:
        """
        folderPath = folderPath if osp.isdir(folderPath) else osp.dirname(folderPath)
        extensions = [".json"]
        jsons = []
        for file in os.listdir(folderPath):
            if file.lower().endswith(tuple(extensions)):
                relativePath = os.path.join(folderPath, file)
                # path = os.path.abspath(relativePath)
                jsons.append(relativePath)
        natural_sort(jsons, key=lambda x: x.lower())
        print("json文件个数:{}".format(len(jsons)))
        return jsons

    def loadAnnoStateFile(self, filePath=""):
        # print('loadAnnoStateFile==============')
        # 默认访问 ./cache/anno_state.json
        result = {}
        if not osp.exists(filePath):
            return {}

        with open(filePath, 'r') as f:
            text = f.read()
            if text:
                data = json.loads(text)
            else:
                data = {}

        # 文件是 key：照片名称 value：字典
        if bool(data):
            for k, v in data.items():
                fm = FileMsg()
                fm.getDataFromDict(v)
                result[k] = fm

                # print("k=",k)
                # print("v=",v)
                # print('fm=',fm.file_state,'  ',fm.file_name,' ',fm.img_state)

        return result

    def loadAutoLabelFile(self, fileFolder=None):
        """
        加载算法运行的文件
        :param fileFolder:
        :return:
        """
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)
        result = {}
        if fileFolder is None or not osp.exists(fileFolder):
            return {}
        files = self.scanAllJsons(fileFolder)
        # print("files=" ,files)
        prename = "autolabel"
        for file in files:
            if prename not in file:
                files.remove(file)

        if len(files) == 0:
            print('行:', sys._getframe().f_lineno, ' ',"没有autolabelxx文件")
            return {}
        # print("files=", files)
        #  默认加载时间最新的文件
        # TODO codecs.open
        with codecs.open(files[-1], 'r', 'utf-8') as f:
        # with open(files[-1], 'r') as f:
            text = f.read()
            if text:
                text_data = json.loads(text)
            else:
                text_data = {}

        if bool(text_data):
            img_list = [osp.basename(p) for p in self.imageList]
            diclabel = text_data.get("data", {})
            for key, value in diclabel.items():
                # 如果json文件内含有文件夹的图片的标签
                if key in img_list:
                    shapes = []
                    for dicshape in value:
                        shape = Shape()
                        shape.getDataFromDict(dicshape)
                        shape.coord_to_points()
                        shape.close()
                        shapes.append(shape)
                    result[key] = shapes
        return result

    def saveAnnoStateFile(self, filePath=""):
        print('行:', sys._getframe().f_lineno, ' ', sys._getframe().f_code.co_name)

        #./cache/anno_state.json
        if osp.dirname(filePath) and not osp.exists(osp.dirname(filePath)):
            os.makedirs(osp.dirname(filePath))

        if not bool(self.fileStateDict):
            return

        try:
            result = {}
            key_list = list(self.fileStateDict.keys())
            natural_sort(key_list, key=lambda x: x.lower())
            for k in key_list:
                result[k] = self.fileStateDict[k].convertToDict()
            # result = {
            #     k: v.convertToDict() for k, v in self.fileStateDict.items()
            # }
            with open(filePath, "w") as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(e)

    def saveLabelInYolo(self, data=None, filename=""):
        """
        将结果保存为yolo格式
        :return:
        """

        if filename:
            if not osp.exists(osp.dirname(filename)):
                os.makedirs(osp.dirname(filename))
        else:
            self.errorMessage(
                self.tr("Error save in yolo"),
                self.tr("Error file: <b>%s</b>") % filename,
            )
            return False

        if data is not None and isinstance(data, AnnoMsg):
            shapes = data.shapes
            if len(shapes) == 0:
                return True
            w = data.imageWidth
            h = data.imageHeight
            if not isinstance(w, (int, float)) or not isinstance(h, (int, float)):
                w = 1920
                h = 1080

            texts = []  # 文本
            for shape in shapes:
                if shape.shape_type != "rectangle" or len(shape.coord_points) != 4:
                    continue
                label = self.participantMap.get(shape.label, -1)
                points = shape.coord_points
                cen_x = (points[0][0] + points[2][0]) / 2
                cen_y = (points[0][1] + points[2][1]) / 2
                box_w = abs(points[2][0] - points[0][0])
                box_h = abs(points[2][1] - points[0][1])
                id_val = shape.id
                attr_val = shape.attr_value
                color_val = int(shape.color) if shape.color is not None else 0
                format_f = lambda x: str(x + .0).ljust(8, '0')[:8]
                # text = "{0} {1} {2} {3} {4} {5} {6} {7}".format(
                #     int(id_val),
                #     int(label),
                #     round(cen_x / w, 6),
                #     round(cen_y / h, 6),
                #     round(box_w / w, 6),
                #     round(box_h / h, 6),
                #     color_val,
                #     attr_val,
                # )
                text = "{0} {1} {2} {3} {4} {5} {6} {7}".format(
                    int(id_val),
                    int(label),
                    format_f(cen_x / w),
                    format_f(cen_y / h),
                    format_f(box_w / w),
                    format_f(box_h / h),
                    color_val,
                    attr_val,
                )
                texts.append(text)

            if len(texts) == 0:
                return True
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    for text in texts:
                        f.write(str(text) + "\n")
                f.close()
                return True
            except Exception as e:
                print(sys._getframe().f_lineno, ": ", e)
                return False
        else:
            return False


    def loadTypeMap(self, classfile):
        """
        读映射关系class.json
        :return:
        """
        if not osp.exists(classfile):
            return {}
        try:
            with open(classfile, "r") as f:
                input_data = f.read()
                outputdict = json.loads(input_data)
                return outputdict
        except Exception as e:
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr("读取类别文件失败: <b>%s，%s</b>") % (classfile, e)
            )
            print(sys._getframe().f_lineno, ": ", e)
            return {}

    def importLabel(self):
        path1=path2=path3=""
        if self.fileDir:
            path1 = osp.join(self.fileDir, self.CACHE,'auto.json')
            path2 = path1
            path3 = osp.join(self.fileDir, self.CACHE, self.LABEL_CACHE)
        # print(self.participantMap)
        # self.participantMap={'person': 0, 'none': 1, 'bicycle': 201, 'electric_bicycle': 301}
        revers_map = {}
        for k, v in self.participantMap.items():
            revers_map[v] = k
        # ext = ".png"
        # if self.fileName:
        #     ext = osp.splitext(self.fileName)[1]

        dirpath = self.fileDir if self.fileDir else ""

        dia = TransfileDialog(revers_map,path1,path2,path3, dirpath)

        dia.exec_()

        self.importDirImages(self.fileDir)

        pass

def save_label_yolo1(data=None, filename="", labeldic=dict()):
    """
            将结果保存为yolo格式
            :return:
            """

    if filename:
        if not osp.exists(osp.dirname(filename)):
            os.makedirs(osp.dirname(filename))
    else:
        print("filename is null")
        return False

    if data is not None and isinstance(data, AnnoMsg):
        shapes = data.shapes
        if len(shapes) == 0:
            return True
        w = data.imageWidth
        h = data.imageHeight
        if not isinstance(w, (int, float)) or not isinstance(h, (int, float)):
            w = 1920
            h = 1080

        texts = []  # 文本
        for shape in shapes:
            if shape.shape_type != "rectangle" or len(shape.coord_points) != 4:
                continue
            label = labeldic.get(shape.label, -1)
            points = shape.coord_points
            cen_x = (points[0][0] + points[2][0]) / 2
            cen_y = (points[0][1] + points[2][1]) / 2
            box_w = abs(points[2][0] - points[0][0])
            box_h = abs(points[2][1] - points[0][1])
            id_val = shape.id
            attr_val = shape.attr_value
            color_val = int(shape.color) if shape.color is not None else 0
            format_f = lambda x: str(x + .0).ljust(8, '0')[:8]
            text = "{0} {1} {2} {3} {4} {5} {6} {7}".format(
                int(id_val),
                int(label),
                format_f(cen_x / w),
                format_f(cen_y / h),
                format_f(box_w / w),
                format_f(box_h / h),
                color_val,
                attr_val,
            )
            texts.append(text)

        if len(texts) == 0:
            return True
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for text in texts:
                    f.write(str(text) + "\n")
            f.close()
            return True
        except Exception as e:
            print(sys._getframe().f_lineno, ": ", e)
            return False
    else:
        return False


def save_label_yolo2(data=None, filename="", labeldic=dict()):
    """
            将结果保存为yolo格式
            :return:
            """

    if filename:
        if not osp.exists(osp.dirname(filename)):
            os.makedirs(osp.dirname(filename))
    else:
        print("filename is null")
        return False

    # 先生成空文件
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("")
    f.close()

    if data is not None and isinstance(data, AnnoMsg):
        shapes = data.shapes
        if len(shapes) == 0:
            # with open(filename, 'w', encoding='utf-8') as f:
            #     f.write("")
            # f.close()
            return True
        w = data.imageWidth
        h = data.imageHeight
        if not isinstance(w, (int, float)) or not isinstance(h, (int, float)):
            w = 1920
            h = 1080

        texts = []  # 文本
        for shape in shapes:
            if shape.shape_type != "rectangle" or len(shape.coord_points) != 4:
                continue
            label = labeldic.get(shape.label, -1)
            points = shape.coord_points
            cen_x = (points[0][0] + points[2][0]) / 2
            cen_y = (points[0][1] + points[2][1]) / 2
            box_w = abs(points[2][0] - points[0][0])
            box_h = abs(points[2][1] - points[0][1])
            id_val = shape.id
            plate_color = shape.plate_color
            plate_num = shape.plate_number if shape.plate_number else '0'

            format_f = lambda x: str(x + .0).ljust(8, '0')[:8]
            text = "{0} {1} {2} {3} {4} {5} {6} {7}".format(
                int(id_val),
                int(label),
                format_f(cen_x / w),
                format_f(cen_y / h),
                format_f(box_w / w),
                format_f(box_h / h),
                plate_color,
                plate_num
            )
            texts.append(text)

        if len(texts) == 0:
            return True
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for text in texts:
                    f.write(str(text) + "\n")
            f.close()
            return True
        except Exception as e:
            print(sys._getframe().f_lineno, ": ", e)
            return False
    else:
        return False




if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = AppEntry()
    win.setWindowIcon(QIcon("wanji_logo64.ico"))
    win.show()

    sys.exit(app.exec_())

