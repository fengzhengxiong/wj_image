# !/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
import time
import json
import os.path as osp



def get_data_from_pplabel(labelpath):
    labeldict = {}
    separator = ['=', '\t', ' ']  # 文件可能的分隔符
    sep = '\t'
    if not os.path.exists(labelpath):
        return {}
    else:
        try:
            with open(labelpath, 'r', encoding='utf-8') as f:
                # 先判定是哪种分割方式
                line = f.readline()
                tmp = line.split(separator[0])
                if len(tmp) == 2:
                    sep = separator[0]
                else:
                    tmp2 = line.split(separator[1])
                    if len(tmp2) == 2:
                        sep = separator[1]
                f.seek(0, 0)  # 恢复文件指针到首部
                # print(f'sep**{sep}**')
                data = f.readlines()
                for each in data:
                    key, val = each.split(sep)
                    file, label = key.strip(), val.strip()
                    if label:
                        label = label.replace('false', 'False')
                        label = label.replace('true', 'True')
                        value = eval(label)
                        for i in range(len(value)):
                            if 'attr' not in value[i].keys():
                                value[i]['attr'] = 0
                        labeldict[file] = value

                    else:
                        labeldict[file] = []
        except Exception as e:
            print(f'error in fun[{sys._getframe().f_code.co_name}], event={e}')
    return labeldict



def labelcxxx_to_jsons(dirpath=None, savepath=None):

    if not osp.exists(dirpath):
        return

    pplabel = get_data_from_pplabel(dirpath)

    alldict = {}

    for k, v in pplabel.items():
        version = "1.0.0"
        updateTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        annoDelay = 0
        datasetName = None
        imagePath = osp.basename(k)
        imageData = None
        imageHeight = 1080
        imageWidth = 1920
        flags = {}

        wholedict = dict(
            version=version,
            updateTime=updateTime,
            annoDelay=annoDelay,
            datasetName=datasetName,
            imagePath=imagePath,
            imageData=imageData,
            imageHeight=imageHeight,
            imageWidth=imageWidth,
            flags=flags,
            shapes=[]
        )

        # print(k, ": ", v)
        k2 = osp.basename(k)
        res = []

        for box in v:
            label = box['transcription']
            id = 0
            coord_points = box['points']
            shape_type = "rectangle"
            attr_value = box['attr']

            outdict = dict(
                label=label,
                points=coord_points,
                shape_type=shape_type,
                bound_box=[],
                id=id,
                group_id=0,
                order_no=v.index(box),
                attr_value=attr_value,
                color=0,
                flags={},
            )
            res.append(outdict)
        wholedict["shapes"] = res
        alldict[k2] = wholedict

    save_path = savepath
    # 保存
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    print("save_path",save_path)
    for k, v in alldict.items():
        print(k,",  ",v)

    # return

    for k, v in alldict.items():
        filename = osp.splitext(k)[0] + ".json"
        filename = osp.join(save_path,filename)
        print(filename)
        try:
            with open(filename, "w") as f:
                json.dump(v, f, ensure_ascii=False, indent=4)
        except Exception as e:
            raise e



if __name__ == '__main__':

    # dirpath = r"C:\Users\wanji\Desktop\test\YOLO_Label"
    # save_path = r"C:\Users\wanji\Desktop\test\Cache.cach"

    dirpath = r"C:\Users\wanji\Desktop\test\Label.cxxx"
    save_path = r"C:\Users\wanji\Desktop\test\JJSS/"
    labelcxxx_to_jsons(dirpath, save_path)






