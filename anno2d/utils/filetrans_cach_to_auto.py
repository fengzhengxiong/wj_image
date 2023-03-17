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


def cachfile_to_autolabel(dirpath=None, savepath=None):
    if not osp.exists(dirpath):
        return

    wholedict=dict(
        alg_name=None,
        file_count=0,
        src_dir=None,
        run_delay=None,
        update_time="",
    )

    labels = {}
    pplabel = get_data_from_pplabel(dirpath)

    shape_type = "rectangle"

    for k, v in pplabel.items():
        # print(k, ": ", v)
        k2 = osp.basename(k)
        res = []
        for box in v:
            outdict = dict(
                label=box['transcription'],
                id=0,
                points=box['points'],
                shape_type=shape_type,
                attr_value=box['attr'],
            )
            res.append(outdict)
        labels[k2] = res

    wholedict.update(
        data=labels,
    )

    wholedict["alg_name"] = None
    wholedict["file_count"] = len(list(pplabel.keys()))
    wholedict["src_dir"] = dirpath
    wholedict["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    save_path = savepath
    # 保存
    if not osp.isdir(save_path):
        save_path = os.path.dirname(save_path)
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    now = time.strftime("%Y%m%d_%H%M%S", time.localtime())

    exalg="autolabel"
    f_name = exalg+now+".json"
    filename = osp.join(save_path, f_name)
    print("filename=", filename)
    # return
    try:
        with open(filename, "w") as f:
            json.dump(wholedict, f, ensure_ascii=False, indent=2)
            return filename
    except Exception as e:
        raise e


if __name__ == '__main__':

    # dirpath = r"C:\Users\wanji\Desktop\test\YOLO_Label"
    # save_path = r"C:\Users\wanji\Desktop\test\Cache.cach"

    dirpath = r"C:\Users\wanji\Desktop\test\Cache.cach"
    save_path = r"C:\Users\wanji\Desktop\test\Cache.cach"
    cachfile_to_autolabel(dirpath, save_path)






