#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PyQt5.QtWidgets import QSpinBox, QAbstractSpinBox
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFontMetrics


class ZoomWidget(QSpinBox):
    def __init__(self, value=100):
        super(ZoomWidget, self).__init__()
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setRange(1, 3000)
        self.setSuffix(' %')
        self.setValue(value)
        self.setToolTip(u'Zoom Level')
        self.setStatusTip(self.toolTip())
        self.setAlignment(Qt.AlignCenter)

    def minimumSizeHint(self):
        height = super(ZoomWidget, self).minimumSizeHint().height()
        fm = QFontMetrics(self.font())
        width = fm.width(str(self.maximum()))
        return QSize(width, height)


# from PyQt5 import QtWidgets
# import sys
#
# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     a = ZoomWidget()
#     a.show()
#
#     sys.exit(app.exec_())