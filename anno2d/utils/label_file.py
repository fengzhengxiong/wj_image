import base64
import contextlib
import io
import json
import os.path as osp

from PyQt5 import QtGui
import PIL.Image

# from labelme import __version__
# from labelme.logger import logger
# from labelme import PY2
# from labelme import QT4
# from labelme import utils

from anno2d import __version__

from anno2d.utils.image import apply_exif_orientation
from anno2d.utils.image import img_arr_to_b64
from anno2d.utils.image import img_b64_to_arr
from anno2d.utils.image import img_data_to_arr
from anno2d.utils.image import img_data_to_pil
from anno2d.utils.image import img_data_to_png_data
from anno2d.utils.image import img_pil_to_data

from anno2d.data.annomsg import AnnoMsg

PIL.Image.MAX_IMAGE_PIXELS = None


# @contextlib.contextmanager
# def open(name, mode):
#     assert mode in ["r", "w"]
#     if PY2:
#         mode += "b"
#         encoding = None
#     else:
#         encoding = "utf-8"
#     yield io.open(name, mode, encoding=encoding)
#     return
@contextlib.contextmanager
def open(name, mode):
    assert mode in ["r", "w"]
    encoding = "utf-8"
    yield io.open(name, mode, encoding=encoding)
    return


class LabelFileError(Exception):
    pass


class LabelFile(object):

    suffix = ".json"

    def __init__(self, filename=None, imgpath=None):
        self.filename = filename  # 标签路径名称
        self.imgpath = imgpath  # 图片路径
        self._annoMsg = AnnoMsg()  # 标注信息读取结构体

        if filename is not None:
            self.load(filename)

    def get_data(self):
        return self._annoMsg

    def set_data(self, data):
        if isinstance(data, AnnoMsg):
            self._annoMsg = data
            return True
        else:
            print('LabelFile.set_data is error')
            return False

    @staticmethod
    def load_image_file(filename):
        if not filename:
            return
        try:
            image_pil = PIL.Image.open(filename)
        except IOError:
            # logger.error("Failed opening image file: {}".format(filename))
            print("Failed opening image file: {}".format(filename))
            return

        # apply orientation to image according to exif
        image_pil = apply_exif_orientation(image_pil)

        with io.BytesIO() as f:
            ext = osp.splitext(filename)[1].lower()
            if ext in [".jpg", ".jpeg"]:
                format = "JPEG"
            else:
                format = "PNG"
            image_pil.save(f, format=format)
            f.seek(0)
            return f.read()

    def load(self, filename):
        # print("load----------", filename)
        try:
            with open(filename, 'r') as f:
                text = f.read()
                if text:
                    data = json.loads(text)
                else:
                    data = {}
            # 字典数据创建结构体元素

            self._annoMsg.getDataFromDict(data)

            # print(" self._annoMsg = ", data)

            # for s in self._annoMsg.shapes:
            #     print(s.coord_points)
            #     print(s.points)

            if self._annoMsg.version:
                if self._annoMsg.version.split(".")[0] != __version__.split(".")[0]:
                    print('文件版本不一致，要注意')

            # if version is None:
            #     logger.warn(
            #         "Loading JSON file ({}) of unknown version".format(
            #             filename
            #         )
            #     )
            # elif version.split(".")[0] != __version__.split(".")[0]:
            #     logger.warn(
            #         "This JSON file ({}) may be incompatible with "
            #         "current labelme. version in file: {}, "
            #         "current version: {}".format(
            #             filename, version, __version__
            #         )
            #     )
            # 图像数据校验
            imageData = None
            if self._annoMsg.imageData is not None:
                imageData = base64.b64decode(self._annoMsg.imageData)
                # if PY2 and QT4:
                #     imageData = img_data_to_png_data(imageData)
            else:
                # TODO 这个分支比较耗时，达到0.5s， 可以考虑cv读取
                # if self.imgpath and osp.exists(self.imgpath):
                #     # imagePath = osp.join(osp.dirname(filename), data["imagePath"])
                #     imageData = self.load_image_file(self.imgpath)
                pass
            if imageData:
                self._annoMsg.imageHeight, self._annoMsg.imageWidth = self._check_image_height_and_width(
                    base64.b64encode(imageData).decode("utf-8"),
                    self._annoMsg.imageHeight,
                    self._annoMsg.imageWidth,
                )

        except Exception as e:
            raise LabelFileError(e)

    def save(self, filename):
        # print("save111")
        if self._annoMsg.imageData is not None:
            imageData = base64.b64encode(self._annoMsg.imageData).decode("utf-8")
            self._annoMsg.imageHeight, self._annoMsg.imageWidth = self._check_image_height_and_width(
                imageData, self._annoMsg.imageHeight, self._annoMsg.imageWidth
            )

        if self._annoMsg.otherData is None:
            self._annoMsg.otherData = {}
        if self._annoMsg.flags is None:
            self._annoMsg.flags = {}

        data = self._annoMsg.convertToDict()

        try:
            with open(filename, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.filename = filename
        except Exception as e:
            raise LabelFileError(e)

    def load22(self, filename):
        keys = [
            "version",
            "imageData",
            "imagePath",
            "shapes",  # polygonal annotations
            "flags",  # image level flags
            "imageHeight",
            "imageWidth",
        ]
        shape_keys = [
            "label",
            "points",
            "group_id",
            "shape_type",
            "flags",
        ]
        try:
            with open(filename, "r") as f:
                data = json.load(f)
            version = data.get("version")
            # if version is None:
            #     logger.warn(
            #         "Loading JSON file ({}) of unknown version".format(
            #             filename
            #         )
            #     )
            # elif version.split(".")[0] != __version__.split(".")[0]:
            #     logger.warn(
            #         "This JSON file ({}) may be incompatible with "
            #         "current labelme. version in file: {}, "
            #         "current version: {}".format(
            #             filename, version, __version__
            #         )
            #     )

            if data["imageData"] is not None:
                imageData = base64.b64decode(data["imageData"])
                # if PY2 and QT4:
                #     imageData = img_data_to_png_data(imageData)
            else:
                # relative path from label file to relative path from cwd
                imagePath = osp.join(osp.dirname(filename), data["imagePath"])
                imageData = self.load_image_file(imagePath)
            flags = data.get("flags") or {}
            imagePath = data["imagePath"]
            self._check_image_height_and_width(
                base64.b64encode(imageData).decode("utf-8"),
                data.get("imageHeight"),
                data.get("imageWidth"),
            )
            shapes = [
                dict(
                    label=s["label"],
                    points=s["points"],
                    shape_type=s.get("shape_type", "polygon"),
                    flags=s.get("flags", {}),
                    group_id=s.get("group_id"),
                    other_data={
                        k: v for k, v in s.items() if k not in shape_keys
                    },
                )
                for s in data["shapes"]
            ]
        except Exception as e:
            raise LabelFileError(e)

        otherData = {}
        for key, value in data.items():
            if key not in keys:
                otherData[key] = value

        # Only replace data after everything is loaded.
        self.flags = flags
        self.shapes = shapes
        self.imagePath = imagePath
        self.imageData = imageData
        self.filename = filename
        self.otherData = otherData

    @staticmethod
    def _check_image_height_and_width(imageData, imageHeight, imageWidth):
        img_arr = img_b64_to_arr(imageData)
        if imageHeight is not None and img_arr.shape[0] != imageHeight:
            # logger.error(
            #     "imageHeight does not match with imageData or imagePath, "
            #     "so getting imageHeight from actual image."
            # )
            imageHeight = img_arr.shape[0]
        if imageWidth is not None and img_arr.shape[1] != imageWidth:
            # logger.error(
            #     "imageWidth does not match with imageData or imagePath, "
            #     "so getting imageWidth from actual image."
            # )
            imageWidth = img_arr.shape[1]
        return imageHeight, imageWidth

    @staticmethod
    def is_label_file(filename):
        return osp.splitext(filename)[1].lower() == LabelFile.suffix

    @staticmethod
    def is_image_file(filename):
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        return filename.lower().endswith(tuple(extensions))


if __name__ == "__main__":

    lls = {}
    lls["a.png"] = {}

    alglabel = dict(
        alg_name="voa",
        file_count=10,
        src_dir=osp.dirname("."),
        run_delay=102.36,
        update_time="20220315..",
        labels=[{},{}],
    )
    filename = "./zz_test.json"
    try:
        with open(filename, "w") as f:
            json.dump(alglabel, f, ensure_ascii=False, indent=4)
    except Exception as e:
        raise LabelFileError(e)