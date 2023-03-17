# !/usr/bin/env python
# -*- coding: utf-8 -*-


import sys

import os
import time


import json
import os.path as osp
import numpy as np
import re
import codecs
import PIL.Image

from PyQt5 import QtGui

tar_dict = {
    0: 'person',
    1: 'none',
    2: 'bicycle',
    3: 'electric_bicycle',
    4: 'motorbike',
    5: 'tricycle',
    6: 'car',
    7: 'suv',
    8: 'Passenger_car',
    9: 'truck_h',
    10: 'truck_k',
    11: 'tractors',
    12: 'bus',
    13: 'Dump_truck',
    14: 'Mixer_truck',
    15: 'tanker',
    16: 'sprinkler',
    17: 'fire_car',
    18: 'police_car',
    19: 'ambulance',
    20: 'traffic_light',
    21: 'tool_vehicle',
}


imgscale_dict = {

}



extent = ".png"

def np_read_txt(path):
    """
    np 读txt  全数据，空格分割
    :param path:
    :return:
    """
    try:
        if not os.path.exists(path):
            return np.array([])
        with open(path, encoding='utf-8') as f:
            recv = np.loadtxt(f, dtype=float, delimiter=" ")
            f.close()
            return recv
    except Exception as e:
        print(f'error in fun[{sys._getframe().f_code.co_name},event={e}]')
        return np.array([])


def read_yolo_txt( path):
    if not os.path.exists(path):
        return
    res = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            line = f.readline()
            while line:
                # print("line= ",line)
                row_data = [data for data in line.strip('\n').split(" ")]
                row_data = [float(a)for a in row_data[:-1]] + [str(row_data[-1])]
                # print(row_data)
                res.append(row_data)
                line = f.readline()
            return res
    except Exception as e:
        print(e)
        return []


def walkFile(file, extensions):
    res = []
    if isinstance(extensions, str):
        suffix = []
        suffix.append(extensions)
    else:
        suffix = list(extensions)
    for root, dirs, files in os.walk(file):
        # root 表示当前正在访问的文件夹路径
        # dirs 表示该文件夹下的子目录名list
        # files 表示该文件夹下的文件list
        print('root:', root)
        print('dirs:', dirs)
        print('files:', files)
        # 遍历文件
        for f in files:
            # print(f, " | ", os.path.join(root, f))
            if f.lower().endswith(tuple(suffix)):
                res.append(os.path.join(root, f))

        # 遍历所有的文件夹
        # for d in dirs:
        #     print(os.path.join(root, d))
    return res


def cur_walkFile(file, extensions):
    if isinstance(extensions, str):
        suffix = []
        suffix.append(extensions)
    else:
        suffix = list(extensions)

    filelist = []

    for root, dirs, files in os.walk(file):
        # for d in dirs:
        #     print os.path.join(root, d)
        # filenames = filter(lambda filename: filename[-4:] == extensions, files)
        # filenames = map(lambda filename: os.path.join(root, filename), filenames)
        # filelist.extend(filenames)
        # print(root)
        # print(dirs)
        # print(files)
        for f in files:
            if f.lower().endswith(tuple(suffix)):
                # path = os.path.join(root, a)
                filelist.append(os.path.join(root, f))
        return filelist

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

def set_tar_dict(path):
    """
       读映射关系class.json
       :return:
       """
    global tar_dict
    if not path:
        return
    if not osp.exists(path):
        return

    try:
        with open(path, "r") as f:
            input_data = f.read()
            outputdict = json.loads(input_data)

            tar_dict.clear()
            for k, v in outputdict.items():
                tar_dict[v] = k

    except Exception as e:

        print(sys._getframe().f_lineno, ": ", e)
        return {}


def natural_sort(list, key=lambda s:s):
    """
    Sort the list into natural alphanumeric order.
    """
    def get_alphanum_key_func(key):
        convert = lambda text: int(text) if text.isdigit() else text
        return lambda s: [convert(c) for c in re.split('([0-9]+)', key(s))]
    sort_key = get_alphanum_key_func(key)
    list.sort(key=sort_key)


def scanAllImages(folderPath):
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

    natural_sort(images, key=lambda x: x.lower())
    # print(images)
    return images


def set_imgscale_dict(dirpath):

    if not dirpath:
        return
    if not osp.exists(dirpath):
        return
    if not osp.isdir(dirpath):
        return

    imglist = scanAllImages(dirpath)
    global imgscale_dict
    if imglist:
        imgscale_dict = {}
        for file in imglist:
            img = PIL.Image.open(file)
            w = img.size[0]
            h = img.size[1]
            ext = osp.splitext(file)[1]
            key = osp.splitext(osp.basename(file))[0]
            imgscale_dict[key] = [w, h, ext]


def get_data_from_txt(path):
    data = np_read_txt(path)
    recvs = data.tolist()
    # print("imgscale_dict = \n",imgscale_dict)
    #
    # print("tar_dict=\n", tar_dict)

    name = osp.splitext(osp.basename(path))[0]
    width, height, ext = imgscale_dict.get(name, [1920, 1080, '.png'])
    d_key = name + ext
    # print(d_key)
    # print('tar_dict=====',tar_dict)

    result = []

    if len(data.shape) == 1:
        recvs = [recvs]

    for recv in recvs:
        cls = int(recv[1])
        id = int(recv[0])
        cls = tar_dict.get(cls, "null")
        # A  B
        # D  C
        x = recv[2]*width
        y = recv[3]*height
        w = recv[4]*width
        h = recv[5]*height
        pA = [x - 0.5 * w, y - 0.5 * h]
        pB = [x + 0.5 * w, y - 0.5 * h]
        pC = [x + 0.5 * w, y + 0.5 * h]
        pD = [x - 0.5 * w, y + 0.5 * h]
        points = [pA,pB,pC,pD]
        shape_type = "rectangle"
        color = int(recv[6])

        if len(recv) >= 8:
            attr = int(recv[-1])
        else:
            attr = 0

        outdict = dict(
            label=cls,
            id=id,
            points=points,
            shape_type=shape_type,
            attr_value=attr,
            color=color,
        )
        result.append(outdict)

    return d_key, result


def get_data_from_txt2(path):
    name = osp.splitext(osp.basename(path))[0]
    # print("imgscale_dict = \n", imgscale_dict)
    # print("tar_dict=\n", tar_dict)
    width, height, ext = imgscale_dict.get(name, [1920, 1080, '.png'])
    d_key = name + ext

    # print(d_key)
    # print('tar_dict=====',tar_dict)

    result = []

    recvs = read_yolo_txt(path)


    for recv in recvs:
        # print(recv)
        if len(recv) != 8:
            print("===========================")
        cls = int(recv[1])
        id = int(recv[0])
        cls = tar_dict.get(cls, "null")
        # A  B
        # D  C
        x = recv[2] * width
        y = recv[3] * height
        w = recv[4] * width
        h = recv[5] * height
        pA = [x - 0.5 * w, y - 0.5 * h]
        pB = [x + 0.5 * w, y - 0.5 * h]
        pC = [x + 0.5 * w, y + 0.5 * h]
        pD = [x - 0.5 * w, y + 0.5 * h]
        points = [pA,pB,pC,pD]
        shape_type = "rectangle"
        plate_color = int(recv[6])

        if type(recv[7]) == str:
            number = recv[7]
        else:
            number = '0'

        outdict = dict(
            label=cls,
            id=id,
            points=points,
            shape_type=shape_type,
            plate_color=plate_color,
            plate_number=number
        )
        result.append(outdict)

    return d_key, result



def txts_to_auolabels(dirpath=None, savepath=None, flag=0):
    """

    :param dirpath:
    :param savepath:
    :param flag: 0 yolo1 , 1: yolo2
    :return:
    """
    if not osp.exists(dirpath):
        return
    save_path = savepath
    filelist = cur_walkFile(dirpath, '.txt')
    # print(filelist)

    wholedict=dict(
        alg_name="voa",
        file_count=10,
        src_dir=osp.dirname("."),
        run_delay=None,
        update_time=None,
    )

    labels = {}
    for Path in filelist:
        if flag==0:
            k, v = get_data_from_txt(Path)
        else:
            k, v = get_data_from_txt2(Path)
        # print(a)
        # print(b)
        labels[k] = v
    # print(Label_dict)

    wholedict.update(
        data=labels,
    )

    wholedict["alg_name"] = None
    wholedict["file_count"] = len(filelist)
    wholedict["src_dir"] = dirpath
    wholedict["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # 保存
    if not osp.isdir(save_path):
        save_path = os.path.dirname(save_path)
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    now = time.strftime("%Y%m%d_%H%M%S", time.localtime())

    exalg="autolabel"
    f_name = exalg+now+".json"
    filename = osp.join(save_path, f_name)
    # print("filename=", filename)
    # return
    try:

        # with open(filename, "w") as f:
        with codecs.open(filename, 'w', 'utf-8') as f:
            json.dump(wholedict, f, ensure_ascii=False, indent=2)
            return filename
    except Exception as e:
        raise e


if __name__ == '__main__':

    dirpath = r"C:\Users\wanji\Desktop\test\YOLO_Label"
    save_path = r"C:\Users\wanji\Desktop\test\Cache.cach"

    dirpath = r"/data/test_new/output/yolo2"
    save_path = r"/data/test_new/cache"

    classjson_path = ""
    img_dirpath = r""

    dirpath = dirpath.replace('\\', '/')
    save_path = save_path.replace('\\', '/')

    set_tar_dict(classjson_path)

    set_imgscale_dict(img_dirpath)

    txts_to_auolabels(dirpath, save_path, 1)






