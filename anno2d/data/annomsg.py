# !/usr/bin/env python
# -*- coding: utf-8 -*-

from anno2d.data.shape import Shape


class AnnoMsg(object):
    """
    标注信息内容
    """

    annoMsgKeys = [
        "version",
        "updateTime",
        "annoDelay",
        "datasetName",
        "imagePath",
        "imageData",
        "flags",  # image level flags
        "imageHeight",
        "imageWidth",
        "shapes",  # polygonal annotations
    ]

    def __init__(self):
        self.version = None
        self.updateTime = ""
        self.annoDelay = 0
        self.datasetName = None
        self.imagePath = None
        self.imageData = None
        self.imageHeight = None
        self.imageWidth = None
        self.flags = {}

        self.shapes = []  # [LabelMsg,]

        self.otherData = {}  # 读取文件有未知数据时暂存这里。

    def getDataFromDict(self, dicData):
        if not isinstance(dicData, dict):
            print("AnnoMsg 输入不是字典")
            return
        self.version = dicData.get("version", None)
        self.updateTime = dicData.get("updateTime", "")
        self.annoDelay = dicData.get("annoDelay", 0)
        self.datasetName = dicData.get("datasetName", None)
        self.imagePath = dicData.get("imagePath", None)
        self.imageData = dicData.get("imageData", None)
        self.imageHeight = dicData.get("imageHeight", None)
        self.imageWidth = dicData.get("imageWidth", None)
        self.flags = dicData.get("flags", {})

        self.shapes.clear()
        shapes_data = dicData.get("shapes", [])
        if shapes_data:
            for data in shapes_data:
                shape = Shape()
                shape.getDataFromDict(data)
                shape.coord_to_points()
                shape.close()
                shape.imgWidth, shape.imgHeight = self.imageWidth, self.imageHeight
                self.shapes.append(shape)

        self.otherData = {
            k: v for k, v in dicData.items() if k not in AnnoMsg.annoMsgKeys
        }

    def convertToDict(self):
        shapes = []
        if self.shapes:
            for s in self.shapes:
                if isinstance(s, Shape):
                    s.points_to_coord()
                    shapes.append(s.convertToDict())
                else:
                    print("AnnoMsg  convertToDict error")
                    continue

        # print("shapes=",shapes)

        data = dict(
            version=self.version,
            updateTime=self.updateTime,
            annoDelay=self.annoDelay,
            datasetName=self.datasetName,
            imagePath=self.imagePath,
            imageData=self.imageData,
            imageHeight=self.imageHeight,
            imageWidth=self.imageWidth,
            flags=self.flags,
            shapes=shapes,
        )
        # print("self.otherData = ", self.otherData)
        for key, value in self.otherData.items():
            assert key not in data
            data[key] = value

        return data

    def reset(self):
        self.version = None
        self.updateTime = ''
        self.annoDelay = 0
        self.datasetName = None
        self.imagePath = None
        self.imageData = None
        self.imageHeight = None
        self.imageWidth = None
        self.flags = {}
        self.shapes = []
        self.otherData = {}

