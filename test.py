#!/usr/bin/env python3
import tree
from transliterator import Transliterator

x = tree.TreeNode('root')
p = x.set_value_for_path("abcd", ('X', 'Y'))
q = x.set_value_for_path("abc", 2)
r = x.set_value_for_path("ab", 3)
s = x.set_value_for_path("a", [4, 5])


print(x.get_own_path())

print(p.get_own_path())
print(p.get_longest_subpath_size())

print(q.get_own_path())
print(q.get_longest_subpath_size())

print(r.get_own_path())
print(r.get_longest_subpath_size())

print(s.get_own_path())
print(s.get_longest_subpath_size())


from utils import SrcBead, DstBead

a = DstBead('A', SrcBead('a'))
b = DstBead('B', SrcBead('b'))

print((a + b + DstBead('C', SrcBead('c')))[1:])


t = Transliterator(x)
print(t('abababcdaabb'))

