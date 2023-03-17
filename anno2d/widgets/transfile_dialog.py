#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

# from widgets.transfile_ui import Ui_Dialog
from anno2d.widgets.transfile_ui import Ui_Dialog
import os
import os.path as osp


from anno2d.utils import filetrans_txts_to_auto
from anno2d.utils.filetrans_txts_to_auto import txts_to_auolabels
from anno2d.utils.filetrans_cach_to_auto import cachfile_to_autolabel
from anno2d.utils.filetrans_cxxx_to_jsons import labelcxxx_to_jsons

from anno2d.utils.qt_func import get_file_path


class TransfileDialog(QDialog, Ui_Dialog):
    def __init__(self, typemap=None, path1='', path2='', path3='', imgpath=""):
        super(TransfileDialog, self).__init__()
        self.setupUi(self)
        if typemap:
            # print(typemap)
            filetrans_txts_to_auto.tar_dict = typemap

        self.img_dirpath = imgpath
        self.lineEdit_7.setText(imgpath)

        #  选择文件路径
        # self.img_dirpath = osp.abspath(".")
        self.last_input = osp.abspath(".")
        self.last_save = osp.abspath(".")
        self.pushButton_10.clicked.connect(self.setImgPath)
        self.pushButton.clicked.connect(self.setInputPath)
        self.pushButton_2.clicked.connect(self.setSavePath)
        self.pushButton_3.clicked.connect(self.trans_txt2autolabel)

        self.last_input2 = osp.abspath(".")
        self.last_save2 = osp.abspath(".")
        self.pushButton_4.clicked.connect(self.setInputPath2)
        self.pushButton_5.clicked.connect(self.setSavePath2)
        self.pushButton_6.clicked.connect(self.trans_cach2autolabel)

        self.last_input3 = osp.abspath(".")
        self.last_save3 = osp.abspath(".")
        self.pushButton_7.clicked.connect(self.setInputPath3)
        self.pushButton_8.clicked.connect(self.setSavePath3)
        self.pushButton_9.clicked.connect(self.trans_cxxx2jsons)

        self.last_save = path1
        self.lineEdit_2.setText(path1)
        self.last_save2 = path2
        self.lineEdit_4.setText(path2)
        self.last_save3 = path3
        self.lineEdit_5.setText(path3)

        self.comboBox.addItems(["yolo txt 颜色+属性", "yolo txt 车牌颜色+车牌号"])
        self.comboBox.setCurrentIndex(0)

    def setImgPath(self):
        img_dirpath = get_file_path(obj_wid=self.lineEdit_7, isfile=False, last_path=self.img_dirpath)
        if img_dirpath == "":
            return
        self.img_dirpath = img_dirpath
        self.lineEdit_7.setText(str(img_dirpath))


    def setInputPath(self):
        input_path = get_file_path(obj_wid=self.lineEdit, isfile=False, last_path=self.last_input)
        if input_path == "":
            return
        self.last_input = input_path
        self.lineEdit.setText(str(input_path))

    def setInputPath2(self):
        input_path = get_file_path(obj_wid=self.lineEdit_3, isfile=True, last_path=self.last_input2)
        if input_path == "":
            return
        self.last_input2 = input_path
        self.lineEdit_3.setText(str(input_path))

    def setInputPath3(self):
        input_path = get_file_path(obj_wid=self.lineEdit_6, isfile=True, last_path=self.last_input3)
        if input_path == "":
            return
        self.last_input3 = input_path
        self.lineEdit_6.setText(str(input_path))

    def setSavePath(self):
        save_path = get_file_path(obj_wid=self.lineEdit_2, isfile=False, last_path=self.last_save)
        if save_path == "":
            return
        self.last_save = save_path
        self.lineEdit_2.setText(str(save_path))

    def setSavePath2(self):
        save_path = get_file_path(obj_wid=self.lineEdit_4, isfile=False, last_path=self.last_save2)
        if save_path == "":
            return
        self.last_save2 = save_path
        self.lineEdit_4.setText(str(save_path))

    def setSavePath3(self):
        save_path = get_file_path(obj_wid=self.lineEdit_5, isfile=False, last_path=self.last_save3)
        if save_path == "":
            return
        self.last_save3 = save_path
        self.lineEdit_5.setText(str(save_path))

    def trans_txt2autolabel(self):
        print('trans_txt2autolabel')

        if osp.exists(self.last_input):
            filetrans_txts_to_auto.set_imgscale_dict(self.img_dirpath)

            filelist = os.listdir(self.img_dirpath)
            # print(filelist)
            for file in filelist:
                if file == "class.json":
                    filetrans_txts_to_auto.set_tar_dict(osp.join(self.img_dirpath, file))
                    # print("=======*/*/*/*/\n", filetrans_txts_to_auto.tar_dict)

            if self.comboBox.currentIndex() == 0:
                file = filetrans_txts_to_auto.txts_to_auolabels(self.last_input, self.last_save)
            else:
                file = filetrans_txts_to_auto.txts_to_auolabels(self.last_input, self.last_save, flag=1)
            QMessageBox.information(self, "Information", "转换完成:{}".format(str(file)))

    def trans_cach2autolabel(self):
        if osp.exists(self.last_input2):
            file = cachfile_to_autolabel(self.last_input2, self.last_save2)
            QMessageBox.information(self, "Information", "转换完成:{}".format(str(file)))

    def trans_cxxx2jsons(self):
        if osp.exists(self.last_input3):
            labelcxxx_to_jsons(self.last_input3, self.last_save3)
            QMessageBox.information(self, "Information", "转换完成:{}".format(str(self.last_save3)))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dia = TransfileDialog()

    sys.exit(dia.exec_())

