from copy import copy


class SugesstItem(object):
    def __init__(self):
        self.term = ""
        self.distance = 0
        self.count = 0

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(self, other.__class__):
            return self.term == other.term
        return False

    def get_hash_code(self):
        return hash(self.term)

    def shallow_copy(self):
        return copy(self)
