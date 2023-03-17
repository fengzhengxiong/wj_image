# !/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import numpy as np

from PyQt5.QtCore import QPointF, QSize


def distance(p):
    return np.sqrt(p.x() * p.x() + p.y() * p.y())


def intersection_point(p1, p2, size: QSize):
    # Cycle through each image edge in clockwise fashion,
    # and find the one intersecting the current line segment.
    # http://paulbourke.net/geometry/lineline2d/
    """
    图像边界交点
    :param p1:
    :param p2:
    :param points: 多边形点list
    :return:
    """
    points = [
        (0, 0),
        (size.width() - 1, 0),
        (size.width() - 1, size.height() - 1),
        (0, size.height() - 1),
    ]

    # x1, y1 should be in the pixmap, x2, y2 should be out of the pixmap
    x1 = min(max(p1.x(), 0), size.width() - 1)
    y1 = min(max(p1.y(), 0), size.height() - 1)
    x2, y2 = p2.x(), p2.y()
    d, i, (x, y) = min(intersecting_edges((x1, y1), (x2, y2), points))
    x3, y3 = points[i]
    x4, y4 = points[(i + 1) % 4]
    if (x, y) == (x1, y1):
        # Handle cases where previous point is on one of the edges.
        if x3 == x4:
            return QPointF(x3, min(max(0, y2), max(y3, y4)))
        else:  # y3 == y4
            return QPointF(min(max(0, x2), max(x3, x4)), y3)
    return QPointF(x, y)


def intersecting_edges(point1, point2, points):
    """Find intersecting edges.

    For each edge formed by `points', yield the intersection
    with the line segment `(x1,y1) - (x2,y2)`, if it exists.
    Also return the distance of `(x2,y2)' to the middle of the
    edge along with its index, so that the one closest can be chosen.
    """
    (x1, y1) = point1
    (x2, y2) = point2
    for i in range(4):
        x3, y3 = points[i]
        x4, y4 = points[(i + 1) % 4]
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        nua = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
        nub = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
        if denom == 0:
            # This covers two cases:
            #   nua == nub == 0: Coincident
            #   otherwise: Parallel
            continue
        ua, ub = nua / denom, nub / denom
        if 0 <= ua <= 1 and 0 <= ub <= 1:
            x = x1 + ua * (x2 - x1)
            y = y1 + ua * (y2 - y1)
            m = QPointF((x3 + x4) / 2, (y3 + y4) / 2)
            d = distance(m - QPointF(x2, y2))
            yield d, i, (x, y)


def distancetoline(point, line):
    p1, p2 = line
    p1 = np.array([p1.x(), p1.y()])
    p2 = np.array([p2.x(), p2.y()])
    p3 = np.array([point.x(), point.y()])
    if np.dot((p3 - p1), (p2 - p1)) < 0:
        return np.linalg.norm(p3 - p1)
    if np.dot((p3 - p2), (p1 - p2)) < 0:
        return np.linalg.norm(p3 - p2)
    if np.linalg.norm(p2 - p1) == 0:
        return 0
    return np.linalg.norm(np.cross(p2 - p1, p1 - p3)) / np.linalg.norm(p2 - p1)


def disDropPoint(p1, p2, point):
    """
    计算点point在向量上投影的距离，有符号
    :param p1: 起点
    :param p2: 末端点
    :param point: 某点
    :return:
    """
    if distance(p2 - p1) < 0.0001:
        return 0.0

    v1 = np.array([p2.x() - p1.x(), p2.y() - p1.y()])
    v2 = np.array([point.x() - p1.x(), point.y() - p1.y()])
    result = np.dot(v1, v2) / np.linalg.norm(v1)
    return result


def projectionPoint(p1, p2, point, def_ret=None):
    """
    点在向量上的投影
    :param p1:
    :param p2:
    :param point:
    :return:
    """
    if distance(p2 - p1) < 0.0001:
        return def_ret
    try:
        v1 = np.array([p2.x() - p1.x(), p2.y() - p1.y()])
        v2 = np.array([point.x() - p1.x(), point.y() - p1.y()])
        dis = np.dot(v1, v2) / np.linalg.norm(v1)
        return scaleEndPoint(p1, p2, dis / distance(p2 - p1))
    except Exception as e:
        print(e)
        return def_ret


def projectionVector(v1, v2, def_ret=None):
    """ v2 向量在v1向量上的投影向量 ，QPointF"""

    if min(distance(v1), distance(v2)) < 0.0001:
        return def_ret
    try:
        vec1 = np.array([v1.x(), v1.y()])
        vec2 = np.array([v2.x(), v2.y()])
        dis = np.dot(vec1, vec2) / np.linalg.norm(vec1)

        return v1 / distance(v1) * dis
    except Exception as e:
        print(e)
        return def_ret


def angleVector(v1, v2, def_ret=None):
    """向量夹角，有方向 = v1逆时针至v2 , 范围-180~180"""
    if min(distance(v1), distance(v2)) < 0.0001:
        return def_ret

    x1, y1 = v1.x(), v1.y()
    x2, y2 = v2.x(), v2.y()
    dot = x1 * x2 + y1 * y2
    det = x1 * y2 - y1 * x2
    theta = np.arctan2(det, dot)
    theta = np.rad2deg(theta)
    # print(theta)
    return theta


def turnPoint(p1, p2, delta_t, def_ret=None):
    """p2点绕p1点旋转，delta_t"""

    if distance(p2 - p1) < 0.00001:
        return def_ret

    v = p2 - p1
    rho = distance(v)
    theta1 = np.arctan2(v.y(), v.x())
    theta2 = theta1 + np.deg2rad(delta_t)
    x = rho * np.cos(theta2)
    y = rho * np.sin(theta2)
    return QPointF(p1.x() + x, p1.y() + y)


def midPoint(p1, p2):
    # return scaleEndPoint(p1, p2, 0.5)
    return QPointF(0.5 * (p1.x() + p2.x()), 0.5 * (p1.y() + p2.y()))


def scaleEndPoint(p1, p2, t):
    """ 原线段比例，求取端点"""
    x = p1.x() + (p2.x() - p1.x()) * t
    y = p1.y() + (p2.y() - p1.y()) * t
    return QPointF(x, y)


def extendline(line, ratio=1, minlength=None):
    """ 以线段中点为准，延长线 """
    p1, p2 = line
    mod_lenth = distance(p2 - p1)
    new_lenth = mod_lenth * ratio
    new_lenth = max(new_lenth, minlength) if minlength is not None else new_lenth
    pw = (p1 + p2) / 2
    new_p1 = (p1 - pw) / (0.5 * mod_lenth) * new_lenth / 2 + pw
    new_p2 = (p2 - pw) / (0.5 * mod_lenth) * new_lenth / 2 + pw
    return [new_p1, new_p2]
