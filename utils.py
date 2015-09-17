import weakref


class SrcBead:

    def __init__(self, val):
        self.v = val
        self.destinations = []

    def _remove_destination(self, weakref_of_dst):
        self.destinations.remove(weakref_of_dst)

    def add_destination(self, dst):
        self.destinations.append(weakref.ref(dst, self._remove_destination))


class DstBead:

    def __init__(self, val, src, flags=()):
        self.v = val
        self.source = src
        self.source.add_destination(self)
        self.flags = flags

    def __add__(self, other):
        return Cord((self, other))

    def __str__(self):
        return "({}/{}{})".format(
            self.v,
            self.source.v,
            '|' + ('|'.join(self.flags)) if self.flags else '')

    def __repr__(self):
        return self.__str__()


class Cord:

    def __init__(self, items=()):
        self._data = tuple(items)

    def __add__(self, other):
        if isinstance(other, Cord):
            return Cord(self._data + other._data)
        elif isinstance(other, DstBead):
            return Cord(self._data + (other,))
        else:
            raise TypeError(
                "Can not concatenate 'Cord' to {}".format(type(other)))

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return Cord(self._data[key])
        else:
            return self._data[key]

    def __str__(self):
        return "".join(map(str, self._data))
