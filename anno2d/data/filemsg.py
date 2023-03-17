# !/usr/bin/env python
# -*- coding: utf-8 -*-


class FileMsg(object):

    # 文件状态 待编辑、已完成、待丢弃
    normalState = 0
    checkState = 1
    abandonState = 2
    # 图片状态 原图、打码
    originImg = 0
    maskImg = 1

    fileMsgKeys = [
        "file_name",
        "file_state",
        "img_state",
        "update_timestamp",
        "anno_delay",
    ]

    def __init__(self, filename=None, dicdata=None):
        self.file_name = filename
        self.file_state = self.normalState
        self.img_state = self.originImg
        self.update_timestamp = None
        self.anno_delay = None

        # TODO 亮度、对比度
        self.other_data = {}

        if dicdata:
            self.getDataFromDict(dicdata)

    def getDataFromDict(self, dicData):
        if not isinstance(dicData, dict):
            print("dicData 输入不是字典")
            return

        _translate = {
            "NORMAL": 0,
            "CHECK": 1,
            "ABANDON": 2,
        }

        self.file_name = dicData.get("file_name", None)
        self.file_state = dicData.get("file_state", "NORMAL")
        self.img_state = dicData.get("img_state", FileMsg.originImg)
        self.update_timestamp = dicData.get("update_timestamp", None)
        self.anno_delay = dicData.get("anno_delay", None)

        self.file_state = _translate[self.file_state]

        self.other_data = {
            k: v for k, v in dicData.items() if k not in FileMsg.fileMsgKeys
        }

    def convertToDict(self):
        data = {}
        _translate = {
            0: "NORMAL",
            1: "CHECK",
            2: "ABANDON",
        }
        try:
            data = dict(
                file_name=self.file_name,
                file_state=_translate[self.file_state],
                img_state=self.img_state,
                update_timestamp=self.update_timestamp,
                anno_delay=self.anno_delay,
            )

            if bool(self.other_data):
                for key, value in self.other_data.items():
                    assert key not in data
                    data[key] = value
        except Exception as e:
            print("convertToDict ", e)

        return data