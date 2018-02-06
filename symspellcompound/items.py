from copy import copy


class SuggestItem(object):
    def __init__(self):
        self.term = ""
        self.distance = 0
        self.count = 0

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(self, other.__class__):
            return self.term == other.term
        return False

    def __str__(self):
        return self.term + ":" + str(self.count) + ":" + str(self.distance)

    def get_hash_code(self):
        return hash(self.term)

    def shallow_copy(self):
        return copy(self)

class DictionaryItem:
    def __init__(self):
        self.suggestions = []
        self.count = 0

