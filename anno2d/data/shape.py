#!/usr/bin/python
# -*- coding: utf-8 -*-


from PyQt5.QtGui import QFont, QColor, QPen, QPainterPath
from PyQt5.QtCore import QRectF
from anno2d.utils.pub import distance, distancetoline
from anno2d.utils.qt_math_util import *
from math import sqrt, pow
import copy
import sys
import math
from anno2d.data.labelmsg import LabelMsg
import numpy as np

from PyQt5 import QtCore
from PyQt5 import QtGui

# 默认，悬浮，选中模式
DEFAULT = 0
HOVERING = 1
SELECTED = 2


DEFAULT_LINE_COLOR = QtGui.QColor(0, 255, 0, 128)  # bf hovering
DEFAULT_FILL_COLOR = QtGui.QColor(0, 255, 0, 60)  # hovering 悬浮填充颜色
DEFAULT_SELECT_LINE_COLOR = QtGui.QColor(255, 255, 255)  # selected
DEFAULT_SELECT_FILL_COLOR = QtGui.QColor(0, 255, 0, 100)  # selected  # 选中后填充颜色
DEFAULT_VERTEX_FILL_COLOR = QtGui.QColor(0, 255, 0, 255)  # 默认点被填充颜色
DEFAULT_HVERTEX_FILL_COLOR = QtGui.QColor(255, 255, 255, 200)  # hovering 点悬浮时候的颜色
MIN_Y_LABEL = 10

# DEFAULT_TEXT_FONT = QtGui.QFont()
# DEFAULT_TEXT_FONT.setPointSize(15)
# DEFAULT_TEXT_FONT.setBold(True)


class ShapeShowMode(object):
    """ shape显示模式 """
    def __init__(self, index=None, mode=DEFAULT):
        self.index = index
        self.mode = mode


class Shape(LabelMsg):
    P_SQUARE = 0
    P_ROUND = 1
    MOVE_VERTEX = 0
    NEAR_VERTEX = 1
    L_SOLID = QtCore.Qt.SolidLine  # 实线
    L_DASH = QtCore.Qt.DashLine  # 虚线

    # 图形种类
    T_POLY = 'polygon'
    T_RECT = 'rectangle'
    T_LINE = 'line'
    T_POINT = 'point'
    T_CIR = 'circle'
    T_LINES = 'linestrip'
    T_BOX = 'box3d'

    BOX_SEQ = [0, 1, 2, 3, 0, 4, 5, 6, 7, 4, 5, 1, 2, 6, 7, 3]
    # The following class variables influence the drawing of all shape objects.
    # of _all_ shape objects.
    line_color = DEFAULT_LINE_COLOR
    fill_color = DEFAULT_FILL_COLOR
    select_line_color = DEFAULT_SELECT_LINE_COLOR
    select_fill_color = DEFAULT_SELECT_FILL_COLOR
    vertex_fill_color = DEFAULT_VERTEX_FILL_COLOR
    hvertex_fill_color = DEFAULT_HVERTEX_FILL_COLOR

    # 顶点模式
    dicVertexMode = {
        DEFAULT: {
            'color': DEFAULT_VERTEX_FILL_COLOR,
            'fillcolor': DEFAULT_VERTEX_FILL_COLOR,
            'style': P_ROUND,
            'size': 5,
        },
        HOVERING: {
            'color': DEFAULT_HVERTEX_FILL_COLOR,
            'fillcolor': DEFAULT_HVERTEX_FILL_COLOR,
            'style': P_SQUARE,
            'size': 10,
        },
        SELECTED: {
            'color': QColor(255, 0, 0, 200),
            'fillcolor': QColor(255, 0, 0, 200),
            'style': P_SQUARE,
            'size': 15,
        },
    }
    # 矩形框线的模式
    dicPolyMode = {
        DEFAULT: {
            'color': DEFAULT_LINE_COLOR,
            'fillcolor': QColor(20, 200, 50, 20),
            'width': 1.0,
        },
        HOVERING: {
            'color': DEFAULT_HVERTEX_FILL_COLOR,
            'fillcolor': QColor(150, 10, 10, 15),
            'width': 1.2,
        },
        SELECTED: {
            'color': QColor(255, 0, 0, 200),
            'fillcolor': QColor(100, 200, 30, 20),
            'width': 1.5,
        },
    }

    text_size = 12
    scale = 1.0
    identified = False  # 是否显示标签字体
    vertexed = True  # 是否显示顶点， TODO 目前仅针对矩形来做修饰

    def __init__(self, label=None, shape_type=None):
        super().__init__(label=label, shape_type=shape_type)
        ''' 成员 '''
        self.label = label
        self.shape_type = shape_type

        self.points = []  # 点位
        self.fill = False  # 是否填充
        self.selected = False  # 是否选中

        self._hlShape = None  # 高亮矩形框
        self._hlVertex = None  # 高亮顶点

        self._closed = False  # 曲线是不是闭合的，如果是，绘制时自动连接到第一个点

        line_color = None
        if line_color is not None:
            self.line_color = line_color
        self._vertex_fill_color = self.vertex_fill_color

    def updateModeDict(self):
        # 顶点模式
        self.dicVertexMode = {
            DEFAULT: {
                'color': self.hvertex_fill_color,
                'fillcolor': self.vertex_fill_color,
                'style': Shape.P_ROUND,
                'size': 5,
            },
            HOVERING: {
                'color': self.hvertex_fill_color,
                'fillcolor': self.hvertex_fill_color,
                'style': Shape.P_SQUARE,
                'size': 10,
            },
            SELECTED: {
                'color': QColor(255, 0, 0, 200),
                'fillcolor': QColor(255, 0, 0, 200),
                'style': Shape.P_SQUARE,
                'size': 15,
            },
        }

        r, g, b = self.select_fill_color.red(), self.select_fill_color.green(), self.select_fill_color.blue()
        # 矩形框线的模式
        self.dicPolyMode = {
            DEFAULT: {
                'color': self.line_color,
                'fillcolor': QColor(r, g, b, 50),
                'width': 1.0,
            },
            HOVERING: {
                'color': self.line_color,
                'fillcolor': QColor(r, g, b, 50),
                'width': 1.2,
            },
            SELECTED: {
                'color': self.select_line_color,
                'fillcolor': QColor(r, g, b, 100),
                'width': 1.5,
            },
        }

    def coord_to_points(self):
        self.points = [QtCore.QPointF(x, y) for x, y in self.coord_points]

    def points_to_coord(self):
        self.coord_points = [(p.x(), p.y()) for p in self.points]

    def updatePoints(self, qp=True):
        """
        更新点位
        :param qp: True 由points更新 ，False coord_points更新
        :return:
        """
        if qp:
            self.points_to_coord()
        else:
            self.coord_to_points()

    def close(self):
        self._closed = True

    def reachMaxPoints(self):
        """
        是否最大点数，目前没用，仅在四边形里用
        :return:
        """
        if len(self.points) >= 4:
            return True
        return False

    def addPoint(self, point):
        if self.points and point == self.points[0]:
            self.close()
        else:
            self.points.append(point)

    def canAddPoint(self):
        return self.shape_type in [self.T_POLY, self.T_LINES]

    def canRemovePoint(self):
        return (self.shape_type in [self.T_POLY, self.T_LINES] and len(self.points) > 3)

    def popPoint(self):
        if self.points:
            return self.points.pop()
        return None

    def insertPoint(self, i, point):
        self.points.insert(i, point)

    def removePoint(self, i):
        self.points.pop(i)

    def isClosed(self):
        return self._closed

    def setOpen(self):
        self._closed = False

    def getRectFromLine(self, pt1, pt2):
        x1, y1 = pt1.x(), pt1.y()
        x2, y2 = pt2.x(), pt2.y()
        return QRectF(x1, y1, x2 - x1, y2 - y1)

    def paint(self, painter):
        if not self.points:
            return

        self.paintEdge(painter)
        self.paintVertex(painter)
        self.paintText(painter)

    def paintEdge(self, painter):
        mode = DEFAULT
        if self._hlShape is not None:
            mode = self._hlShape.mode

        mode = SELECTED if self.selected else mode
        linewidth = self.dicPolyMode.get(mode, {}).get('width', 1.0)
        color = self.dicPolyMode.get(mode, {}).get('color', self.line_color)
        fillcolor = self.dicPolyMode.get(mode, {}).get('fillcolor', None)  # 如果为None, 不填充

        pen = QPen(color)
        linewidth = max(linewidth, linewidth / self.scale)
        pen.setWidthF(linewidth)
        painter.setPen(pen)

        if self.shape_type == self.T_BOX:
            line_path = self.makePath()
            painter.drawPath(line_path)

            paths = self.makePlanePath()
            for pa in paths:
                painter.fillPath(pa, fillcolor)
        else:
            line_path = self.makePath()
            painter.drawPath(line_path)
            if self.fill and fillcolor:
                painter.fillPath(line_path, fillcolor)

    def paintVertex(self, painter):
        """默认均为DEFAULT，某顶点被hover或select ，其他为hover状态"""

        painter.setPen(QPen())
        # 矩形情况下，不填充状态下可不显示顶点
        if self.shape_type in [self.T_RECT, self.T_CIR] and \
                not self.vertexed and not self.fill:
            return

        if self._hlVertex is not None and self._hlVertex.mode == SELECTED:
            index = self._hlVertex.index
            mode = self._hlVertex.mode
            self.drawVertex(painter, [index], mode)
            p_list = list(range(len(self.points)))
            if index in p_list:
                p_list.remove(index)
            # print(p_list)

            self.drawVertex(painter, p_list, HOVERING)

        else:
            mode = DEFAULT if self._hlVertex is None else self._hlVertex.mode
            p_list = list(range(len(self.points)))
            self.drawVertex(painter, p_list, mode)

    def drawVertex(self, painter, indexs, mode):
        """
        绘制顶点
        :param painter: QPainter()
        :param indexs: 索引列表
        :param mode: 点的状态模式
        :return:
        """
        path = QPainterPath()
        d = self.dicVertexMode.get(mode, {}).get('size', 5)
        color = self.dicVertexMode.get(mode, {}).get('fillcolor', self._vertex_fill_color)
        p_type = self.dicVertexMode.get(mode, {}).get('style', self.P_SQUARE)
        d = d / self.scale

        for i in indexs:
            point = self.points[i]
            if p_type == self.P_SQUARE:
                path.addRect(point.x() - d / 2, point.y() - d / 2, d, d)
            elif p_type == self.P_ROUND:
                path.addEllipse(point, d / 2.0, d / 2.0)

        painter.drawPath(path)
        painter.fillPath(path, color)

    def paintText(self, painter):
        if self.identified:
            font = QFont()
            # textsize = min(self.text_size, self.text_size/self.scale)
            textsize = self.text_size / self.scale

            textsize = np.clip(textsize, self.text_size / 2.8, self.text_size / 0.4)
            font.setPointSizeF(textsize)
            painter.setFont(font)
            min_x = min([point.x() for point in self.points])
            min_y = min([point.y() for point in self.points])
            # text = "{}-{}-{}".format(
            #     self.order_no,
            #     self.id,
            #     self.label
            # )
            text = "{}-{}".format(
                self.order_no,
                self.label
            )
            min_y = max(min_y, 1.25 * textsize)
            painter.drawText(QtCore.QPointF(min_x, min_y), text)

    def nearestVertex(self, point, epsilon):
        min_distance = float("inf")
        min_i = None
        for i, p in enumerate(self.points):
            dist = distance(p - point)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                min_i = i
        return min_i

    def nearestEdge(self, point, epsilon):
        min_distance = float("inf")
        post_i = None
        for i in range(len(self.points)):
            line = [self.points[i - 1], self.points[i]]
            dist = distancetoline(point, line)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                post_i = i
        return post_i

    def containsPoint(self, point):
        """
        是否包含某个点
        :param point:
        :return:
        """
        return self.makePath().contains(point)

    def getCircleRectFromLine(self, line):
        """Computes parameters to draw with `QPainterPath::addEllipse`"""
        if len(line) != 2:
            return None
        (c, point) = line
        r = line[0] - line[1]
        d = sqrt(pow(r.x(), 2) + pow(r.y(), 2))
        rectangle = QRectF(c.x() - d, c.y() - d, 2 * d, 2 * d)
        return rectangle

    def makePath(self):
        """
        创建绘制路径
        :return:
        """
        path = QPainterPath()
        if self.shape_type == self.T_RECT:
            if len(self.points) == 4:
                path.moveTo(self.points[0])
                for p in self.points[1:]:
                    path.lineTo(p)
                if self.isClosed():
                    path.lineTo(self.points[0])
        elif self.shape_type == self.T_CIR:
            if len(self.points) == 2:
                rectangle = self.getCircleRectFromLine(self.points)
                path.addEllipse(rectangle)
        elif self.shape_type == self.T_LINE:
            if len(self.points) == 2:
                path.moveTo(self.points[0])
                path.lineTo(self.points[1])
        elif self.shape_type in [self.T_POLY, self.T_POINT]:
            path.moveTo(self.points[0])
            for p in self.points[1:]:
                path.lineTo(p)
            if self.isClosed():
                path.lineTo(self.points[0])
        elif self.shape_type == self.T_BOX:
            if len(self.points) == 8:
                path.moveTo(self.points[0])
                for i in self.BOX_SEQ:
                    path.lineTo(self.points[i])
        else:
            path.moveTo(self.points[0])
            for p in self.points[1:]:
                path.lineTo(p)

        return path

    def makePlanePath(self):
        """
        针对3Dbox 框，建立6平面路径
        :return:
        """
        # 定义点序列
        # 3--------0
        # |        |-----  车的方向
        # 2--------1
        # 面的顺序：前、后、左、右、上、下
        seqs = [
            [0, 1, 5, 4],
            [3, 2, 6, 7],
            [0, 4, 7, 3],
            [1, 5, 6, 2],
            [4, 5, 6, 7],
            [0, 1, 2, 3],
        ]
        paths = []
        if self.shape_type == self.T_BOX and len(self.points) == 8:
            for seq in seqs:
                path = QPainterPath()
                path.moveTo(self.points[seq[0]])
                for idx in seq:
                    path.lineTo(self.points[idx])
                path.lineTo(self.points[seq[0]])
                paths.append(path)

        return paths

    def boundingRect(self):
        """
        返回包围盒QRectF
        :return:
        """
        if self.shape_type == self.T_POINT and len(self.points) == 1:
            return QRectF(self.points[0].x(), self.points[0].y(), 0.2, 0.2)
        return self.makePath().boundingRect()

    def moveBy(self, offset):
        self.points = [p + offset for p in self.points]

    def moveVertexBy(self, i, offset):
        self.points[i] = self.points[i] + offset

    def changeByVertex(self, i, offset):
        """
        改变2D框——通过一个顶点
        :param i: 顶点索引
        :param offset: 偏移矢量
        :return:
        """

        if self.shape_type == self.T_RECT:
            if len(self.points) == 4:
                self.changeRect(i, offset)
        elif self.shape_type == self.T_BOX:
            pass
        else:
            self.moveVertexBy(i, offset)

    def changeRect(self, i, offset):
        """
        矩形结构变化
        :param i: 顶点index
        :param offset:
        :return:
        """
        # 设i点为C，变为C1， 对角点=A点不动，根据C1调节B、D
        pc, pd, pa, pb = self.points[i], self.points[(i + 1) % 4], self.points[(i + 2) % 4], self.points[
            (i + 3) % 4]

        pc1 = pc + offset
        pb1 = projectionPoint(pa, pb, pc1)
        pd1 = projectionPoint(pa, pd, pc1)
        if None in [pb1, pd1]:
            return
        # 加异常判定，长度不可以接近0，否则图形坍缩，不能继续编辑了
        dist = min(distance(pb1 - pa), distance(pd1 - pa))
        if dist <= 2:
            return

        new_points = [pc1, pd1, pa, pb1]
        for j in range(4):
            self.points[(i + j) % 4] = new_points[j]
        self.updatePoints()

    def changeQuad(self, i, offset):
        """
        平行四边形结构
        :param i:顶点index
        :param offset:
        :return:
        """
        # i-1 点平移量 delta是 offset在（i-2,i-1）
        v1 = self.points[(i + 3) % 4] - self.points[(i + 2) % 4]
        off1 = projectionVector(v1, offset)

        v2 = self.points[(i + 1) % 4] - self.points[(i + 2) % 4]
        off2 = projectionVector(v2, offset)
        # TODO 需要做防坍缩处理
        self.moveVertexBy(i, offset)
        self.moveVertexBy((i + 3) % 4, off1)
        self.moveVertexBy((i + 1) % 4, off2)
        self.updatePoints()

    def changeByMove(self, i, offset):
        """
        图形平移
        :param i: 平移线索引，如果为None，平移
        :param offset:
        :return:
        """
        delta = offset
        if delta:
            if self.shape_type == self.T_BOX:
                pass
            else:
                self.moveBy(delta)
                self.updatePoints()

    def highlightPoly(self, i, action):
        self._hlShape = ShapeShowMode(i, mode=action)

    def highlightVertex(self, i, action):
        self._hlVertex = ShapeShowMode(i, mode=action)

    def highlightClear(self):
        self._hlShape = None
        self._hlVertex = None

    def copy(self):
        # shape = Shape("%s" % self.label)
        # shape.points = [p for p in self.points]
        # shape.fill = self.fill
        # shape.selected = self.selected
        # shape._closed = self._closed
        # if self.line_color != Shape.line_color:
        #     shape.line_color = self.line_color
        # if self.fill_color != Shape.fill_color:
        #     shape.fill_color = self.fill_color
        # return shape
        c_shape = copy.deepcopy(self)

        return c_shape

    def __len__(self):
        return len(self.points)

    def __getitem__(self, key):
        return self.points[key]

    def __setitem__(self, key, value):
        self.points[key] = value
