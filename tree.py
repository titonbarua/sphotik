import operator
from functools import reduce
from collections import deque


class TreeNode:

    def __init__(self, key, value=None, parent=None):
        self.key = key
        self.value = value
        self.parent = parent
        self.children = {}

        if parent is None:
            self.key = 'root'
            self.parent = None
        else:
            self.parent.children[key] = self

    def set_value_for_path(self, path, value):
        current_node = self
        for key in path:
            current_node = (
                current_node.children[key]
                if key in current_node.children
                else TreeNode(key=key, value=None, parent=current_node))
        current_node.value = value
        return current_node

    def get_value_for_path(self, path):
        current_node = self
        for key in path:
            current_node = current_node.children[key]
        return current_node.value

    def path_is_leaf(self, path):
        current_node = self
        for key in path:
            current_node = current_node.children[key]
        return not bool(current_node.children)

    def get_own_path(self, relative_to=None):
        path, current_node = [], self

        while True:
            # Reached absolute root.
            if current_node.parent is None:
                break

            # Reached relative root.
            if current_node == relative_to:
                break

            path = [current_node.key] + path
            current_node = current_node.parent

        return path

    def get_longest_subpath_size(self):
        def collect_subpath_size(node, path_size):
            if len(node.children) == 0:
                return [path_size]

            return reduce(
                operator.add,
                [
                    collect_subpath_size(cn, path_size + 1)
                    for cn in node.children.values()
                ]
            )

        return max(collect_subpath_size(self, 0))

    def transform(self, func):
        """ Traverse through all the paths with values in the
        tree and transform each value with a function.

        The signature of the transforming function is:
            func(path, value, isleaf) -> new_value
        """
        nodes_to_traverse = deque()
        nodes_to_traverse.appendleft(([], self))

        try:
            while True:
                parent_path, node = nodes_to_traverse.pop()
                path = parent_path + [node.key]
                node.value = func(
                    path, node.value, len(node.children) > 0)

                for child in node.children.values():
                    nodes_to_traverse.appendleft((path, child))
        except IndexError:
            pass

        return self

    def __str__(self):
        nodes = set()

        def register(path, value, isleaf):
            nodes.add("{} -> {}".format(" / ".join(path), value))
            return value

        for c in self.children.values():
            c.transform(register)

        return "\n".join(sorted(nodes))
