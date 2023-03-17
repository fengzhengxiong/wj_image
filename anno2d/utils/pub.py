# -*- coding: utf-8 -*-
# !/usr/bin/env python


# from math import sqrt

import re
import sys
import numpy as np
import os.path as osp


from PyQt5.QtCore import QT_VERSION_STR, QRegExp
# from PyQt5.QtGui import QColor, QIcon, QRegExpValidator


class struct(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def distance(p):
    return np.sqrt(p.x() * p.x() + p.y() * p.y())


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


def have_qstring():
    '''p3/qt5 get rid of QString wrapper as py3 has native unicode str type'''
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))


# def util_qt_strlistclass():
#     return QStringList if have_qstring() else list


def natural_sort(list, key=lambda s:s):
    """
    Sort the list into natural alphanumeric order.
    """
    def get_alphanum_key_func(key):
        convert = lambda text: int(text) if text.isdigit() else text
        return lambda s: [convert(c) for c in re.split('([0-9]+)', key(s))]
    sort_key = get_alphanum_key_func(key)
    list.sort(key=sort_key)



def search_path_reference(input_path, isfile=False):
    """
    路径的模糊匹配
    :param input_path:
    :param isfile: 是不是文件路径
    :return:
    """
    output_path = None
    if isfile is True:
        if osp.exists(input_path) and osp.isfile(input_path):
            output_path = input_path
            return output_path
    if input_path:
        if osp.exists(input_path) and osp.isdir(input_path):
            output_path = input_path
        else:
            if osp.exists(osp.dirname(input_path)):
                output_path = osp.dirname(input_path)
            else:
                if osp.exists(osp.abspath(osp.join(input_path, ".."))):
                    output_path = osp.abspath(osp.join(input_path, ".."))
    return output_path