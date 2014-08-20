

class MyClass(object):

    def __init__(self, val):
        self._val = val

    def foo(self):
        return self._val

    @property
    def read_only_prop(self):
        return self._val

    @property
    def writeable_prop(self):
        return self._val

    @writeable_prop.setter
    def writeable_prop(self, val):
        self._val = val

    @writeable_prop.deleter
    def writeable_prop(self):
        del self._val





