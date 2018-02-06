from .data import INSERTION_COST, SHIFT_COST, DELETION_COST, SUBSTITUTION_COST, \
    layout_coords_dict, simple_layout
import numpy as np
import time

from unidecode import unidecode


class InsertionAction:
    def __init__(self, i, c):
        self.i = i
        self.c = c

    def cost(self, s):
        return insertion_cost(s, self.i, self.c)

    def perform(self, s):
        return s[:self.i] + self.c + s[self.i:]


class SubstitutionAction:
    def __init__(self, i, c):
        self.i = i
        self.c = c

    def cost(self, s):
        return substitution_cost(s, self.i, self.c)

    def perform(self, s):
        return s[:self.i] + self.c + s[(self.i + 1):]


class DeletionAction:
    def __init__(self, i):
        self.i = i

    def cost(self, s):
        return deletion_cost(s, self.i)

    def perform(self, s):
        return s[:self.i] + s[(self.i + 1):]


# Returns the keyboard layout c "lives in"; for instance, if c is A, this will
# return the shifted keyboard array, but if it is a, it will return the regular
# keyboard array.  Raises a ValueError if character is in neither array
def array_for_char(c, layout):
    for array in layout_coords_dict[layout]:
        print(array)
        if array.get(c) is not None:
            return layout_coords_dict[layout][0]
    raise ValueError(c + " not found in any keyboard layouts")


# Finds the Euclidean distance between two characters, regardless of whether
# they're shifted or not.
def euclidean_keyboard_distance_old(c1, c2, layout):
    coord1 = array_for_char(c1, layout=layout).get(c1)
    coord2 = array_for_char(c2, layout=layout).get(c2)
    return ((coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2) ** 0.5


def euclidean_keyboard_distance(c1, c2, layout):
    coord1 = simple_layout[layout].get(c1)
    coord2 = simple_layout[layout].get(c2)
    if coord1 is None: print("None type {}".format(c1))
    if coord2 is None: print("None type {}".format(c2))
    return ((coord1[0] - coord2[0]) ** 2 + (coord1[1] - coord2[1]) ** 2) ** 0.5


# The cost of inserting c at position i in string s
def insertion_cost_old(s, i, c, layout):
    if not s or i >= len(s):
        return INSERTION_COST
    cost = INSERTION_COST
    if array_for_char(s[i], layout=layout) != array_for_char(c, layout=layout):
        # We weren't holding down the shift key when we were typing the original
        # string, but started holding it down while inserting this character, or
        # vice versa.  Either way, this action should have a higher cost.
        cost += SHIFT_COST
    cost += euclidean_keyboard_distance(s[i], c, layout=layout)
    return cost


def insertion_cost(s, i, c, layout):
    if not s or i >= len(s):
        return INSERTION_COST
    cost = INSERTION_COST
    cost += euclidean_keyboard_distance(s[i], c, layout=layout)
    return cost


# The cost of omitting the character at position i in string s
def deletion_cost(s, i):
    return DELETION_COST


# The cost of substituting c at position i in string s
def substitution_cost_old(s, i, c, layout):
    cost = SUBSTITUTION_COST
    if len(s) == 0 or i >= len(s):
        return INSERTION_COST
    if array_for_char(s[i], layout=layout) != array_for_char(c, layout=layout):
        # We weren't holding down the shift key when we were typing the original
        # string, but started holding it down while inserting this character, or
        # vice versa.  Either way, this action should have a higher cost.
        cost += SHIFT_COST
    cost += euclidean_keyboard_distance(s[i], c, layout=layout)
    return cost


def substitution_cost(s, i, c, layout):
    cost = SUBSTITUTION_COST
    if len(s) == 0 or i >= len(s):
        return INSERTION_COST
    cost += euclidean_keyboard_distance(s[i], c, layout=layout)
    return cost


# Finds the typo distance (a floating point number) between two strings, based
# on the canonical Levenshtein distance algorithm.
def typo_distance(s, t, layout='QWERTY'):
    # A multidimensional array of 0s with len(s) rows and len(t) columns.
    # d = [[0] * (len(t) + 1) for i in range(len(s) + 1)]
    s, t = unidecode(s), unidecode(t)
    d = np.zeros((len(s) + 1, len(t) + 1))

    for i in range(len(s) + 1):
        d[i][0] = sum([deletion_cost(s, j - 1) for j in range(i)])

    for i in range(len(t) + 1):
        intermediateString = ""
        cost = 0.0
        for j in range(i):
            cost += insertion_cost(intermediateString, j - 1, t[j - 1], layout=layout)
            intermediateString = intermediateString + t[j - 1]
        d[0][i] = cost

    for j in range(1, len(t) + 1):
        for i in range(1, len(s) + 1):
            if s[i - 1] == t[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                delCost = deletion_cost(s, i - 1)
                insertCost = insertion_cost(s, i, t[j - 1], layout=layout)
                subCost = substitution_cost(s, i - 1, t[j - 1], layout=layout)
                d[i][j] = min(d[i - 1][j] + delCost,
                              d[i][j - 1] + insertCost,
                              d[i - 1][j - 1] + subCost)

    return d[len(s)][len(t)]


if __name__ == "__main__":
    # time1 = datetime.datetime.now()
    # print(typo_distance("cete", "cette", "AZERTY"))
    # time2 = datetime.datetime.now()
    # print((time2 - time1).total_seconds())
    # time1 = datetime.datetime.now()
    # print(damerau_levenshtein_distance("cete", "cette"))
    # time2 = datetime.datetime.now()
    # print((time2 - time1).total_seconds())
    start_time = time.time()
    print(typo_distance("cête", "cette", "AZERTY"))
    print("--- %s seconds ---" % (time.time() - start_time))
