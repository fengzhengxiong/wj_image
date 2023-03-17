# !/usr/bin/env python
# -*- coding: utf-8 -*-


class LabelMsg(object):
    """
    标签信息结构体数据，与json文件项对应，被Shape继承
    """

    labelMsgKeys = [
        "label",
        "points",
        "shape_type",
        "bound_box",
        "id",
        "group_id",
        "order_no",
        "attr_value",
        "color",
        "plate_number",
        "plate_color",

        "flags",
    ]

    def __init__(self, label=None, coord_points=list(), shape_type=None, bound_box=list(),
             id=0, group_id=None, order_no=None, attr_value=0, color=0, plate_number='',
             plate_color=0):
        self.label = label  # 标签类别
        self.coord_points = coord_points  # 点(x,y)
        self.shape_type = shape_type
        self.bound_box = bound_box  # 包围盒,矩形是自身，点、线没有包围盒
        self.id = id  # 标签id
        self.group_id = group_id
        self.order_no = order_no  # 标签序号
        self.attr_value = attr_value  # 属性值
        self.color = color  # 车辆颜色
        self.flags = {}  # 框的标志位
        self.plate_number = plate_number  # 车牌号
        self.plate_color = plate_color  # 车牌颜色0~4 ,0123 蓝黄绿白, 4非车牌

        self.otherData = {}

        # 以免跨文件复制时得不到更新
        self.imgWidth = None  # 标签所属图像宽高
        self.imgHeight = None

    def getDataFromDict(self, dicData):
        if not isinstance(dicData, dict):
            print("LabelMsg 输入不是字典")
            return

        self.label = dicData.get("label", "")
        self.coord_points = dicData.get("points", [])
        self.shape_type = dicData.get("shape_type", None)
        self.bound_box = dicData.get("bound_box", [])
        self.id = dicData.get("id", 0)
        self.group_id = dicData.get("group_id", None)
        self.order_no = dicData.get("order_no", 0)
        self.attr_value = dicData.get("attr_value", 0)
        self.color = dicData.get("color", 0)
        self.plate_number = dicData.get("plate_number", '')
        self.plate_color = dicData.get("plate_color", 0)

        self.flags = dicData.get("flags", {})

        self.otherData = {
            k: v for k, v in dicData.items() if k not in LabelMsg.labelMsgKeys
        }

    def convertToDict(self):
        data = {}
        try:
            data = dict(
                label=self.label,
                points=self.coord_points,
                shape_type=self.shape_type,
                bound_box=self.bound_box,
                id=self.id,
                group_id=self.group_id,
                order_no=self.order_no,
                attr_value=self.attr_value,
                color=self.color,
                plate_number=self.plate_number,
                plate_color=self.plate_color,
                flags=self.flags,
            )
            for key, value in self.otherData.items():
                assert key not in data
                data[key] = value
        except Exception as e:
            print("convertToDict ", e)

        return data

