# !/usr/bin/env python
# -*- coding: utf-8 -*-

# import queue


class MyQueue():
    """
    自定义缓存队列，支持undo，redo
    未加锁...
    """
    MAX_SIZE = 20  # 最大长度

    def __init__(self, max_size=None):
        self.data = []
        self.index = None  # 当前数据索引
        self._max_size = max_size if (max_size and max_size > 0) else self.MAX_SIZE

    def put(self, val):
        """
        放入index下个位置数据
        :param val:
        :return:
        """
        # print('put------')
        if self.index is None:
            self.data = []
        else:
            # index 之后的数据舍弃
            # print(self.index, len(self.data))
            if self.index < len(self.data) - 1:
                # print('put  ********')
                tmp = self.data[: (self.index + 1)]
                self.data = tmp
            while self.isFull():
                self.getFront()

        self.data.append(val)
        self.index = len(self.data) - 1
        # self.index = self.data.index(val)

    def getLast(self, def_ret=None):
        """
        undo操作
        :param def_ret:
        :return:
        """
        if self.isGetLast():
            self.index -= 1
            return self.data[self.index]
        else:
            return def_ret

    def getNext(self, def_ret=None):
        """
        redo操作
        :param def_ret:
        :return:
        """
        if self.isGetNext():
            self.index += 1
            return self.data[self.index]
        else:
            return def_ret

    def getFront(self, def_ret=None):
        if not self.isEmpty():
            return self.data.pop(0)
        return def_ret

    def getThis(self, def_ret=None):
        if not self.isEmpty():
            return self.data[self.index]
        return def_ret

    def reset(self):
        self.data = []
        self.index = None

    def isEmpty(self):
        return len(self.data) < 1

    def isFull(self):
        return len(self.data) >= self._max_size

    def isGetLast(self):
        """
        是否可以获取上一个
        :return:
        """
        if self.isEmpty():
            return False
        if self.index is None or self.index == 0:
            return False
        return True


    def isGetNext(self):
        """
        是否可以获取下一个
        :return:
        """
        if self.isEmpty():
            return False
        if self.index is None or self.index == len(self.data) - 1:
            return False
        return True

    def count(self):
        return len(self.data)



if __name__ == '__main__':

    a = MyQueue(10)
    a.put([1,2,3,4])
    a.put([5,6,7])
    a.put(["a",'bcd'])
    a.put([9,8,7,6])
    # a.put([5,4,3333])

    a.getLast()
    a.getLast()
    a.getLast()
    a.getLast()
    a.getLast()
    a.getLast()

    print(a.index, len(a.data))
    print(a.data)
    a.put([10000])
    a.put([20000])
    a.getLast()
    a.getLast()
    a.getLast()
    print(a.index, len(a.data))
    print(a.data)

    #
    # print('-------------')
    # x = a.getLast()
    # print(x)
    #
    # print('-------------')
    # x = a.getLast()
    # print(x)
    #
    # print('============')
    # x = a.getNext()
    # print(x)
    #
    # a.put([100000])
    # a.getLast()
    #
    # print('============')
    # x = a.getNext()
    # print(x)

