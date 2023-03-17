# !/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QWidget, QApplication, QMenu, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QPointF, QRectF, QLineF
from PyQt5.QtGui import QPainter, QColor, QCursor, QPixmap, QBrush

from anno2d.data.shape import Shape
from anno2d.utils.pub import distance, distancetoline

from anno2d.utils.myqueue import MyQueue
from anno2d.utils.qt_math_util import *


CURSOR_DEFAULT = Qt.ArrowCursor
CURSOR_POINT = Qt.PointingHandCursor
CURSOR_DRAW = Qt.CrossCursor
CURSOR_MOVE = Qt.ClosedHandCursor
CURSOR_GRAB = Qt.OpenHandCursor
CURSOR_MOVE_IMG = Qt.SizeAllCursor

MOVE_SPEED = 2.0
# class Canvas(QGLWidget):
MOVE_IMG_STEP = 50
# TODO backup
# TODO drawing color

# 默认，悬浮，选中模式
DEFAULT = 0
HOVERING = 1
SELECTED = 2


class Canvas(QWidget):
    zoomRequest = pyqtSignal(int, QPointF)
    scrollRequest = pyqtSignal(int, int, bool)
    newShape = pyqtSignal()
    selectionChanged = pyqtSignal(list)
    shapeMoved = pyqtSignal()
    drawingPolygon = pyqtSignal(bool)
    vertexSelected = pyqtSignal(bool)
    coordChanged = pyqtSignal(float, float)

    CREATE, EDIT, MOSAIC = 0, 1, 2

    _createMode = "polygon"
    _fill_drawing = False  # draw shadows  绘制过程是否填充
    double_click = "close"
    epsilon = 9.0
    num_backups = 30

    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)

        self.mode = self.EDIT
        self.pixmap = QPixmap()
        self.scale = 1.0
        self._painter = QPainter()
        self._cursor = CURSOR_DEFAULT
        self.setFocusPolicy(Qt.StrongFocus)

        self.shapes = []
        self.shapesBackups = MyQueue(max_size=self.num_backups)
        self.current = None  # 这个是指当前正在创建的框
        self.selectedShapes = []  # save the selected shapes here
        self.selectedShapesCopy = []

        self.line = Shape()
        self.prevPoint = QPointF()  # 记录拖动时候上一个点位置
        self.prevMovePoint = QPointF()  # 当前实时移动的坐标，moveevent刷新的
        self.offsets = QPointF(), QPointF()  # 点在选中框包围盒中相对位置，与坐上，与右下

        self.visible = {}

        self.hShape = None
        self.hVertex = None
        self.hEdge = None
        self.prevhVertex = None
        self.prevhShape = None
        self.prevhEdge = None

        self.movingShape = False

        self.snapping = True  # 画多边形时，是否碰触第一个点，按alt 不去碰触
        self.hShapeIsSelected = False
        self.arounding = False  # 拉框框选时，是否正在选取

        self.menus = (QMenu(), QMenu())

        self.panStartPos = QPointF()  # 移动图片用的，起始点位
        self.roundStartPos = QPointF()  # 框选起始点位
        self.maskStartPos = QPointF()  # masoic起点位置

    def fillDrawing(self):
        return self._fill_drawing

    def setFillDrawing(self, value):
        self._fill_drawing = value

    def setScale(self, value):
        self.scale = value

    @property
    def createMode(self):
        return self._createMode

    @createMode.setter
    def createMode(self, value):
        if value not in [
            "polygon",
            "rectangle",
            "circle",
            "line",
            "point",
            "linestrip",
        ]:
            raise ValueError("Unsupported createMode: %s" % value)
        self._createMode = value

    def storeShapes(self):
        tmp = []
        for shape in self.shapes:
            tmp.append(shape.copy())
        self.shapesBackups.put(tmp)
        # print("shapesBackups,idx={},len={}".format(self.shapesBackups.index, self.shapesBackups.count()))

    def isShapeRestorable(self, undo=True):
        """
        能否回退、下一步
        :param undo:True 回退 ，False 下一步
        :return:
        """
        if undo:
            return self.shapesBackups.isGetLast()
        else:
            return self.shapesBackups.isGetNext()

    def restoreShape(self, undo=True):
        """
        从备份队列里恢复上一步存储
        :return:
        """
        if not self.isShapeRestorable(undo):
            return

        # 获取堆栈上一个缓存
        if undo:
            shapesBackup = self.shapesBackups.getLast([])
        else:
            shapesBackup = self.shapesBackups.getNext([])
        self.shapes = []
        self.selectedShapes = []
        for s in shapesBackup:
            c = s.copy()
            c.selected = False
            self.shapes.append(c)

        self.visible = {}
        self.update()

    def orderShapes(self):
        """
        序号更新
        :return:
        """
        if self.shapes:
            for shape in self.shapes:
                shape.order_no = self.shapes.index(shape)

    def isShapeVisible(self, shape):
        return self.visible.get(shape, True)

    def drawing(self):
        return self.mode == self.CREATE

    def editing(self):
        return self.mode == self.EDIT

    def mosaicing(self):
        return self.mode == self.MOSAIC

    def setMode(self, mode=EDIT):
        self.mode = mode
        if mode != Canvas.EDIT:
            self.unHighlight()
            self.deSelectShape()

    def unHighlight(self):
        if self.hShape:
            self.hShape.highlightClear()
            self.update()
        self.prevhShape = self.hShape
        self.prevhVertex = self.hVertex
        self.prevhEdge = self.hEdge
        self.hShape = self.hVertex = self.hEdge = None

    def selectedVertex(self):
        return self.hVertex is not None

    def selectedEdge(self):
        return self.hEdge is not None

    def addPointToEdge(self):
        shape = self.prevhShape
        index = self.prevhEdge
        point = self.prevMovePoint
        if shape is None or index is None or point is None:
            return
        shape.insertPoint(index, point)
        shape.highlightVertex(index, HOVERING)
        self.hShape = shape
        self.hVertex = index
        self.hEdge = None
        self.movingShape = True

    def removeSelectedPoint(self):
        '''
        删除点位，限制删除类型为多边形和折线，并且大于3个点
        :return:
        '''
        shape = self.prevhShape
        index = self.prevhVertex
        if shape is None or index is None:
            return
        if shape.canRemovePoint():
            shape.removePoint(index)
            shape.highlightClear()
        self.hShape = shape
        self.prevhVertex = None
        self.movingShape = True  # Save changes

    def handleMoveEventArounding(self, ev):
        """
        处理框选过程
        :param ev:
        :return: 是否结束事件流程
        """
        # pos = self.transformPos(ev.pos())
        # 判断shape在框内
        w = self.prevMovePoint.x() - self.roundStartPos.x()
        h = self.prevMovePoint.y() - self.roundStartPos.y()
        box = QRectF(self.roundStartPos.x(), self.roundStartPos.y(), w, h)
        selected_count = len(self.selectedShapes)

        for shape in self.shapes:
            if self.isShapeVisible(shape):
                # shape.selected = False
                if box.contains(shape.boundingRect()):
                    if shape not in self.selectedShapes:
                        self.selectedShapes.append(shape)
                else:
                    if shape in self.selectedShapes:
                        shape.selected = False
                        self.selectedShapes.remove(shape)

        # 减少触发频率，检测到框数目不同再触发
        if len(self.selectedShapes) != selected_count:
            # print('count= ',len(self.selectedShapes), ' ', selected_count)
            self.selectionChanged.emit(self.selectedShapes)
        self.repaint()
        return True

    def handleMoveEventDrawing(self, ev):
        """
        处理绘制过程中鼠标移动
        :param ev:
        :return:
        """
        pos = self.transformPos(ev.pos())

        self.line.shape_type = self.createMode
        self.overrideCursor(CURSOR_DRAW)
        if not self.current:
            self.repaint()
            return True
        if self.outOfPixmap(pos):
            # Don't allow the user to draw outside the pixmap.
            # Project the point to the pixmap's edges.
            pos = self.intersectionPoint(self.current[-1], pos)
        elif (
                self.snapping
                and len(self.current) > 1
                and self.createMode == "polygon"
                and self.closeEnough(pos, self.current[0])
        ):
            # Attract line to starting point and
            # colorise to alert the user.
            # 多边形闭合，回到起点后，鼠标点显示比较大
            pos = self.current[0]
            self.overrideCursor(CURSOR_POINT)
            self.current.highlightVertex(0, HOVERING)
        if self.createMode in ["polygon", "linestrip"]:
            self.line[0] = self.current[-1]
            self.line[1] = pos
        elif self.createMode == "rectangle":
            self.line.shape_type = "line"
            self.line.points = [self.current[0], pos]
            self.line.close()
            self.handleDrawing(pos)
        elif self.createMode == "circle":
            self.line.points = [self.current[0], pos]
            self.line.shape_type = "circle"
        elif self.createMode == "line":
            self.line.points = [self.current[0], pos]
            self.line.close()
        elif self.createMode == "point":
            self.line.points = [self.current[0]]
            self.line.close()
        self.repaint()
        self.current.highlightClear()
        return True

    def handleMoveEventPressing(self, ev):
        """
        处理鼠标按下拖动逻辑，中键无需处理，已在其他函数
        :param ev:
        :return:
        """
        pos = self.transformPos(ev.pos())

        ''' 处理右键拖动框 '''
        if Qt.RightButton & ev.buttons():
            if self.selectedShapesCopy and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMoveShapes(self.selectedShapesCopy, pos)
                self.repaint()
            elif self.selectedShapes:
                self.selectedShapesCopy = [
                    s.copy() for s in self.selectedShapes
                ]
                self.repaint()
            return True

        ''' 处理左键拖动框或者顶点 '''
        if Qt.LeftButton & ev.buttons():
            if self.selectedVertex():
                self.boundedMoveVertex(pos)
                # self.shapeMoved.emit()
                self.repaint()
                self.movingShape = True
            elif self.selectedShapes and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMoveShapes(self.selectedShapes, pos)
                self.repaint()
                self.movingShape = True
            return True

    def handleMoveEventHovering(self, ev):
        """
        处理鼠标悬浮
        :param ev:
        :return:
        """
        # Just hovering over the canvas, 2 posibilities:
        # - Highlight shapes
        # - Highlight vertex
        # Update shape/vertex fill and tooltip value accordingly.
        pos = self.transformPos(ev.pos())

        self.setToolTip(self.tr("Image"))
        lstShapesHoverOrder = []  # 被选中的最优先遍历
        for shape in reversed([s for s in self.shapes if self.isShapeVisible(s)]):
            if shape.selected:
                lstShapesHoverOrder.insert(0, shape)
            else:
                lstShapesHoverOrder.append(shape)

        for shape in lstShapesHoverOrder:
            index = shape.nearestVertex(pos, self.epsilon / self.scale)
            index_edge = shape.nearestEdge(pos, self.epsilon / self.scale)
            if index is not None:
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.prevhVertex = self.hVertex = index
                self.prevhShape = self.hShape = shape
                self.prevhEdge = self.hEdge
                self.hEdge = None
                shape.highlightVertex(index, HOVERING)
                self.overrideCursor(CURSOR_POINT)
                self.setToolTip(self.tr("Click & drag to move point"))
                self.setStatusTip(self.toolTip())
                self.update()
                break
            elif index_edge is not None and shape.canAddPoint():
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.prevhVertex = self.hVertex
                self.hVertex = None
                self.prevhShape = self.hShape = shape
                self.prevhEdge = self.hEdge = index_edge
                self.overrideCursor(CURSOR_POINT)
                self.setToolTip(self.tr("Click to create point"))
                self.setStatusTip(self.toolTip())
                self.update()
                break
            elif shape.containsPoint(pos):
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.prevhVertex = self.hVertex
                self.hVertex = None
                self.prevhShape = self.hShape = shape
                self.prevhEdge = self.hEdge
                self.hEdge = None
                self.setToolTip(
                    self.tr("Click & drag to move shape '%s'") % shape.label
                )
                self.setStatusTip(self.toolTip())
                self.overrideCursor(CURSOR_GRAB)
                self.update()
                break
        else:  # Nothing found, clear highlights, reset state.
            self.overrideCursor(CURSOR_DEFAULT)
            self.unHighlight()
        self.vertexSelected.emit(self.hVertex is not None)
        return True

    def loadPixmap(self, pixmap, clear_shapes=True):
        self.pixmap = pixmap
        if clear_shapes:
            self.shapes = []
        self.update()

    def loadShapes(self, shapes, replace=True):
        if replace:
            self.shapes = list(shapes)
        else:
            self.shapes.extend(shapes)
        self.orderShapes()
        self.storeShapes()
        self.current = None
        self.hShape = None
        self.hVertex = None
        self.hEdge = None
        self.update()

    def setShapeVisible(self, shape, value):
        self.visible[shape] = value
        self.update()

    def resetState(self):
        self.restoreCursor()
        self.pixmap = None
        self.scale = 1.0
        self.shapesBackups.reset()
        self.update()

    def transformPos(self, point: QPointF):
        return QPointF(point.x() / self.scale, point.y() / self.scale) - self.offsetToCenter()

    def offsetToCenter(self):
        s = self.scale
        area = super(Canvas, self).size()
        w, h = self.pixmap.width() * s, self.pixmap.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QPointF(x, y)

    def reset(self):
        self.pixmap = QPixmap()
        self.scale = 1.0
        self.update()

    def paintEvent(self, event):
        p = self._painter
        p.begin(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.HighQualityAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.scale(self.scale, self.scale)
        p.translate(self.offsetToCenter())
        # 清理一次
        p.eraseRect(QRectF(0, 0, self.size().width(), self.size().height()))
        if self.pixmap:
            p.drawPixmap(0, 0, self.pixmap)

        Shape.scale = self.scale
        for shape in self.shapes:
            if self.isShapeVisible(shape):
                shape.fill = shape.selected or shape == self.hShape
                shape.paint(p)
        if self.current:
            # 绘制过程中，可以加特效
            brush = QBrush(Qt.BDiagPattern)
            p.setBrush(brush)
            self.current.paint(p)  # 画当前的框
            self.line.paint(p)  # 画线段

        if self.selectedShapesCopy:
            for s in self.selectedShapesCopy:
                s.paint(p)

        if (
                self.fillDrawing()
                and self.createMode == "polygon"
                and self.current is not None
                and len(self.current.points) >= 2
        ):
            # 多边形绘制过程中的填充
            drawing_shape = self.current.copy()
            drawing_shape.addPoint(self.line[1])
            drawing_shape.fill = True
            drawing_shape.paint(p)

        # 这段画 画的 尺度线  和 背景调色板  self.prevPoint在原来的 画的过程中  边成了0,0
        if self.drawing() and not self.prevMovePoint.isNull() and not self.outOfPixmap(self.prevMovePoint):
            # print('self.prevMovePoint', self.prevMovePoint)
            p.setPen(QColor(0, 0, 0, 255))

            p.drawLine(QLineF(self.prevMovePoint.x(), 0, self.prevMovePoint.x(), self.pixmap.height()))
            p.drawLine(QLineF(0, self.prevMovePoint.y(), self.pixmap.width(), self.prevMovePoint.y()))

        # 框选中...
        if self.arounding:
            # print('++++++++')
            w = self.prevMovePoint.x() - self.roundStartPos.x()
            h = self.prevMovePoint.y() - self.roundStartPos.y()
            p.setPen(QColor(255, 255, 255, 255))
            # brush = QBrush(Qt.BDiagPattern)
            # p.setBrush(brush)
            p.drawRect(QRectF(self.roundStartPos.x(), self.roundStartPos.y(), w, h))
            p.fillRect(QRectF(self.roundStartPos.x(), self.roundStartPos.y(), w, h),
                       QColor(20, 10, 200, 20))

        p.end()

    def mouseMoveEvent(self, ev):
        # print('mouseMoveEvent')
        pos = self.transformPos(ev.pos())
        self.prevMovePoint = pos
        # 更新像素坐标，采取信号方式
        self.coordChanged.emit(self.prevMovePoint.x(), self.prevMovePoint.y())

        ''' 中键按下拖动，移动图片，无论何种模式下'''
        if Qt.MiddleButton & ev.buttons():
            # 平移图片
            self.overrideCursor(CURSOR_MOVE_IMG)
            # self.setCursor(CURSOR_MOVE_IMG)
            delta_x = pos.x() - self.panStartPos.x()
            delta_y = pos.y() - self.panStartPos.y()
            self.scrollRequest.emit(delta_x, Qt.Horizontal, True)
            self.scrollRequest.emit(delta_y, Qt.Vertical, True)
            self.update()
            return

        ''' 框选状态，优先处理，没有填充高亮 '''
        if self.editing() and self.arounding and Qt.LeftButton & ev.buttons():
            if self.handleMoveEventArounding(ev):
                return

        '''绘制过程  '''
        if self.drawing():
            self.handleMoveEventDrawing(ev)

        if self.editing():
            if Qt.RightButton & ev.buttons() or Qt.LeftButton & ev.buttons():
                self.handleMoveEventPressing(ev)
            else:
                self.handleMoveEventHovering(ev)


    def mousePressEvent(self, ev):
        pos = self.transformPos(ev.pos())
        try:
            if ev.button() == Qt.LeftButton:
                if self.drawing():
                    if self.current:
                        # Add point to existing shape.
                        if self.createMode == "polygon":
                            self.current.addPoint(self.line[1])
                            self.line[0] = self.current[-1]
                            if self.current.isClosed():
                                self.finalise()
                        elif self.createMode in ["circle", "line"]:
                            assert len(self.current.points) == 1
                            self.current.points = self.line.points
                            self.finalise()
                        elif self.createMode == "rectangle":
                            # assert len(self.current.points) == 4
                            if len(self.current.points) == 4:
                                self.handleDrawing(pos)
                                self.finalise()
                            else:
                                self.current = None
                                self.drawingPolygon.emit(False)
                                self.update()

                        elif self.createMode == "linestrip":
                            self.current.addPoint(self.line[1])
                            self.line[0] = self.current[-1]
                            if int(ev.modifiers()) == Qt.ControlModifier:
                                self.finalise()

                    elif not self.outOfPixmap(pos):
                        self.current = Shape(shape_type=self.createMode)
                        self.current.addPoint(pos)
                        if self.createMode == "point":
                            self.finalise()
                        else:
                            self.line.points = [pos, pos]
                            self.drawingPolygon.emit(True)
                            self.update()

                elif self.editing():
                    if self.selectedEdge() and int(ev.modifiers()) == Qt.AltModifier:
                        # alt + 左键点中顶点，添加点
                        self.addPointToEdge()
                    elif self.selectedVertex() and int(ev.modifiers()) == Qt.ShiftModifier:
                        # Delete point if: left-click + SHIFT on a point ，shift+左键点中顶点，删除之
                        self.removeSelectedPoint()

                    group_mode = int(ev.modifiers()) == Qt.ControlModifier
                    # selection = self.selectShapePoint(pos)
                    target = self.selectShapePoint(pos, multiple_selection_mode=group_mode)
                    self.prevPoint = pos
                    self.repaint()
                    if target is None:
                        # 如果没有选择的，左键就是框选
                        self.roundStartPos = pos
                        self.arounding = True

                elif self.mosaicing():
                    # TODO 马赛克
                    # self.overrideCursor(CURSOR_DRAW)
                    # self.maskStartPos = pos
                    pass

            elif ev.button() == Qt.RightButton and self.editing():
                group_mode = int(ev.modifiers()) == Qt.ControlModifier
                # 已经有选中的，并且右键新的不在已选之列，则新增一个hShape
                if not self.selectedShapes or (
                        self.hShape is not None
                        # and self.hShape not in self.selectedShapes  #  注释这个解决bug：右键拖动位置偏差大问题
                ):
                    self.selectShapePoint(pos, multiple_selection_mode=group_mode)
                    self.repaint()
                self.prevPoint = pos

            elif ev.button() == Qt.MiddleButton:
                self.overrideCursor(CURSOR_MOVE_IMG)
                self.panStartPos = pos
            self.update()
        except Exception as e:
            print(e)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.RightButton:
            if self.editing():
                # menu = self.menus[bool(self.selectedShapeCopy)]
                menu = self.menus[len(self.selectedShapesCopy) > 0]
                self.restoreCursor()
                if (
                        not menu.exec_(self.mapToGlobal(ev.pos()))
                        and self.selectedShapesCopy
                ):
                    # Cancel the move by deleting the shadow copy.
                    self.selectedShapesCopy = []
                    self.repaint()
            elif self.drawing():
                self.undoLastPoint()

        elif ev.button() == Qt.LeftButton:
            if self.editing():
                if (
                        self.hShape is not None
                        and self.hShapeIsSelected
                        and not self.movingShape
                ):
                    self.selectionChanged.emit(
                        [x for x in self.selectedShapes if x != self.hShape]
                    )

                if self.arounding:
                    self.arounding = False  # 框选模式使能关闭
                    self.repaint()

        elif ev.button() == Qt.MiddleButton:
            self.restoreCursor()

        if self.movingShape and self.hShape:
            index = self.shapes.index(self.hShape)
            cur_one = self.shapesBackups.getThis()
            if cur_one and cur_one[index].points != self.shapes[index].points:
                self.storeShapes()
                self.shapeMoved.emit()

            self.movingShape = False

    def endMove(self, copy=False):
        """
        右键拖动结束后，菜单选项
        :param copy:
        :return:
        """
        assert self.selectedShapes and self.selectedShapesCopy
        assert len(self.selectedShapesCopy) == len(self.selectedShapes)
        if copy:
            for i, shape in enumerate(self.selectedShapesCopy):
                self.shapes.append(shape)
                self.selectedShapes[i].selected = False  # 选中的切换状态
                self.selectedShapes[i] = shape  # 替换为copy的作为选中的
        else:
            for i, shape in enumerate(self.selectedShapesCopy):
                self.selectedShapes[i].points = shape.points  # 仅是移动，替换点位信息即可
        self.selectedShapesCopy = []
        self.repaint()
        self.orderShapes()
        self.storeShapes()
        return True

    def handleDrawing(self, pos):
        if self.createMode == "rectangle":
            if self.current:
                pointA = self.current[0]
                pointC = pos
                # AB CD 分别水平
                pointB = QPointF(pointC.x(), pointA.y())
                pointD = QPointF(pointA.x(), pointC.y())
                self.current.points = [pointA, pointB, pointC, pointD]
                self.current.close()

    def canCloseShape(self):
        return self.drawing() and self.current and len(self.current) > 2

    def mouseDoubleClickEvent(self, ev):
        # We need at least 4 points here, since the mousePress handler
        # adds an extra one before this handler is called.
        if ev.button() == Qt.LeftButton:
            if (
                    self.double_click == "close"
                    and self.canCloseShape()
                    and len(self.current) > 3
            ):
                # print('mouseDoubleClickEvent====')
                self.current.popPoint()
                self.finalise()

    def selectShapes(self, shapes):
        self.selectionChanged.emit(shapes)
        self.update()

    def selectShapePoint(self, point, multiple_selection_mode=False):
        """
        鼠标点位选中顶点，或者框
        :param point: QPointF()
        :param multiple_selection_mode:  多选模式
        :return: ret，点击在空白处，返回None
        """
        ret = None
        if self.selectedVertex():  # A vertex is marked for selection.
            index, shape = self.hVertex, self.hShape
            shape.highlightVertex(index, SELECTED)
            ret = self.hVertex
        else:
            for shape in reversed(self.shapes):
                if self.isShapeVisible(shape) and shape.containsPoint(point):
                    if shape not in self.selectedShapes:
                        if multiple_selection_mode:
                            self.selectionChanged.emit(
                                self.selectedShapes + [shape]
                            )
                        else:
                            self.selectionChanged.emit([shape])
                        self.hShapeIsSelected = False
                    else:
                        self.hShapeIsSelected = True
                    self.calculateOffsets(point)
                    ret = shape
                    return ret
        self.deSelectShape()
        return ret

    def calculateOffsets(self, point):
        """
        计算点在选中框中的相对坐标
        :param point: QPointF()
        :return:
        """
        left = self.pixmap.width() - 1
        right = 0
        top = self.pixmap.height() - 1
        bottom = 0
        for s in self.selectedShapes:
            rect = s.boundingRect()
            if rect.left() < left:
                left = rect.left()
            if rect.right() > right:
                right = rect.right()
            if rect.top() < top:
                top = rect.top()
            if rect.bottom() > bottom:
                bottom = rect.bottom()

        x1 = left - point.x()
        y1 = top - point.y()
        x2 = right - point.x()
        y2 = bottom - point.y()
        self.offsets = QPointF(x1, y1), QPointF(x2, y2)

    def snapPointToCanvas(self, x, y):
        """
        Moves a point x,y to within the boundaries of the canvas.
        :return: (x,y,snapped) where snapped is True if x or y were changed, False if not.
        """
        if x < 0 or x > self.pixmap.width() or y < 0 or y > self.pixmap.height():
            x = max(x, 0)
            y = max(y, 0)
            x = min(x, self.pixmap.width())
            y = min(y, self.pixmap.height())
            return x, y, True

        return x, y, False

    def boundedMoveVertex(self, pos):
        index, shape = self.hVertex, self.hShape
        point = shape[index]
        if self.outOfPixmap(pos):
            pos = self.intersectionPoint(point, pos)
        delta_pos = pos - point
        shape.changeByVertex(index, delta_pos)

    def boundedMoveShapes(self, shapes, pos):
        """
        多个框一起移动
        :param shapes:
        :param pos:
        :return:
        """
        if self.outOfPixmap(pos):
            return False  # No need to move
        o1 = pos + self.offsets[0]
        if self.outOfPixmap(o1):
            pos -= QPointF(min(0, o1.x()), min(0, o1.y()))
        o2 = pos + self.offsets[1]
        if self.outOfPixmap(o2):
            pos += QPointF(
                min(0, self.pixmap.width() - o2.x()),
                min(0, self.pixmap.height() - o2.y()),
            )
        # XXX: The next line tracks the new position of the cursor
        # relative to the shape, but also results in making it
        # a bit "shaky" when nearing the border and allows it to
        # go outside of the shape's area for some reason.
        # self.calculateOffsets(self.selectedShapes, pos)
        dp = pos - self.prevPoint
        if dp:
            for shape in shapes:
                shape.changeByMove(None, dp)
            self.prevPoint = pos
            return True
        return False

    def deSelectShape(self):
        if self.selectedShapes:
            self.selectionChanged.emit([])
            self.hShapeIsSelected = False
            self.update()

    def deleteSelected(self):
        deleted_shapes = []
        if self.selectedShapes:
            for shape in self.selectedShapes:
                self.shapes.remove(shape)
                deleted_shapes.append(shape)
            self.orderShapes()
            self.storeShapes()
            self.selectedShapes = []
            self.update()
        return deleted_shapes

    def duplicateSelectedShapes(self):
        if self.selectedShapes:
            self.selectedShapesCopy = [s.copy() for s in self.selectedShapes]
            self.boundedShiftShapes(self.selectedShapesCopy)
            self.endMove(copy=True)
        return self.selectedShapes

    def boundedShiftShapes(self, shapes):
        """
        仅用于拷贝时产生，偏移
        :param shapes:
        :return:
        """
        # Try to move in one direction, and if it fails in another.
        # Give up if both fail.
        point = shapes[0][0]
        offset = QPointF(4.0, 4.0)
        self.offsets = QPointF(), QPointF()
        # self.calculateOffsets(shape, point)
        self.prevPoint = point
        if not self.boundedMoveShapes(shapes, point - offset):
            self.boundedMoveShapes(shapes, point + offset)

    def outOfPixmap(self, p):
        w, h = self.pixmap.width(), self.pixmap.height()
        return not (0 <= p.x() <= w - 1 and 0 <= p.y() <= h - 1)

    def finalise(self):
        assert self.current
        self.current.close()
        self.shapes.append(self.current)
        self.current.order_no = self.shapes.index(self.current)
        self.orderShapes()
        self.storeShapes()
        self.current = None
        self.newShape.emit()
        self.update()

    def closeEnough(self, p1, p2):
        return distance(p1 - p2) < (self.epsilon / self.scale)

    def intersectionPoint(self, p1, p2):
        size = self.pixmap.size()
        return intersection_point(p1, p2, size)

    def wheelEvent(self, ev):
        if not hasattr(ev, "angleDelta"):
            return
        delta = ev.angleDelta()
        h_delta = delta.x()
        v_delta = delta.y()
        mods = ev.modifiers()
        if Qt.ControlModifier == int(mods) and v_delta:
            self.scrollRequest.emit(delta.x(), Qt.Horizontal, False)
            self.scrollRequest.emit(delta.y(), Qt.Vertical, False)
        else:
            if v_delta:
                self.zoomRequest.emit(v_delta, ev.pos())

        ev.accept()  # 将事件接收不再上传，用ignore 图片平移不准

    def moveByKeyboard(self, offset):
        if self.selectedShapes:
            self.boundedMoveShapes(
                self.selectedShapes, self.prevPoint + offset
            )
            self.repaint()
            self.movingShape = True

    def keyPressEvent(self, ev):
        modifiers = ev.modifiers()
        key = ev.key()
        if self.drawing():
            if key == Qt.Key_Escape and self.current:
                self.current = None
                self.drawingPolygon.emit(False)
                self.update()
            elif key == Qt.Key_Return and self.canCloseShape():
                self.finalise()
            elif modifiers == Qt.AltModifier:
                self.snapping = False
        elif self.editing():
            move_dic = {
                Qt.Key_A: (MOVE_IMG_STEP, Qt.Horizontal, False),
                Qt.Key_D: (-MOVE_IMG_STEP, Qt.Horizontal, False),
                Qt.Key_W: (MOVE_IMG_STEP, Qt.Vertical, False),
                Qt.Key_S: (-MOVE_IMG_STEP, Qt.Vertical, False),
            }
            if key in move_dic.keys():
                dis, direct, flg = move_dic[key]
                self.scrollRequest.emit(dis, direct, flg)

            move_dic2 = {
                Qt.Key_Up: QPointF(0.0, -MOVE_SPEED),
                Qt.Key_Down: QPointF(0.0, MOVE_SPEED),
                Qt.Key_Left: QPointF(-MOVE_SPEED, 0.0),
                Qt.Key_Right: QPointF(MOVE_SPEED, 0.0),
            }
            if key in move_dic2.keys():
                self.moveByKeyboard(move_dic2[key])

        # ev.ignore()
        super(Canvas, self).keyPressEvent(ev)

    def keyReleaseEvent(self, ev):
        modifiers = ev.modifiers()
        if self.drawing():
            if int(modifiers) == 0:
                self.snapping = True
        elif self.editing():
            if self.movingShape and self.selectedShapes:
                index = self.shapes.index(self.selectedShapes[0])
                cur_one = self.shapesBackups.getThis()
                if cur_one and cur_one[index].points != self.shapes[index].points:
                    self.storeShapes()
                    self.shapeMoved.emit()

                self.movingShape = False

    def setLastLabel(self, text, flags):
        ''' 被主界面调用的，新增标签后修改 '''
        assert text
        self.shapes[-1].label = text
        self.shapes[-1].flags = flags
        self.shapesBackups.getLast()
        self.orderShapes()
        self.storeShapes()
        # print("self.shapes[-1]=",self.shapes[-1])
        return self.shapes[-1]

    def undoLastLine(self):
        assert self.shapes
        self.current = self.shapes.pop()
        self.current.setOpen()
        if self.createMode in ["polygon", "linestrip"]:
            self.line.points = [self.current[-1], self.current[0]]
        elif self.createMode in ["rectangle", "line", "circle"]:
            self.current.points = self.current.points[0:1]
        elif self.createMode == "point":
            self.current = None
        self.drawingPolygon.emit(True)

    def undoLastPoint(self):
        if not self.current or self.current.isClosed():
            return
        self.current.popPoint()
        if len(self.current) > 0:
            self.line[0] = self.current[-1]
        else:
            self.current = None
            self.drawingPolygon.emit(False)
        self.update()

    # These two, along with a call to adjustSize are required for the
    # scroll area.
    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.pixmap:
            return self.scale * self.pixmap.size()
        return super(Canvas, self).minimumSizeHint()

    def resizeEvent(self, event):
        # print('canview resizeEvent')
        super(Canvas, self).resizeEvent(event)


    def enterEvent(self, event):
        self.setMouseTracking(True)
        self.setFocus()
        self.overrideCursor(self._cursor)
        super(Canvas, self).enterEvent(event)

    def leaveEvent(self, event):
        self.restoreCursor()
        super(Canvas, self).leaveEvent(event)
        self.clearFocus()
        self.setMouseTracking(False)

    def focusOutEvent(self, ev):
        self.restoreCursor()

    def currentCursor(self):
        cursor = QApplication.overrideCursor()
        if cursor is not None:
            cursor = cursor.shape()
        return cursor

    def overrideCursor(self, cursor):
        self._cursor = cursor
        if self.currentCursor() is None:
            QApplication.setOverrideCursor(cursor)
        else:
            QApplication.changeOverrideCursor(cursor)

    def restoreCursor(self):
        QApplication.restoreOverrideCursor()


