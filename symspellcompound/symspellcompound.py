# -*- coding: utf-8 -*-

"""Main module."""
import os
from copy import copy
import math
from pyxdameraulevenshtein import damerau_levenshtein_distance, normalized_damerau_levenshtein_distance, \
    damerau_levenshtein_distance_ndarray, normalized_damerau_levenshtein_distance_ndarray
import time

from symspellcompound.errors import DistanceException
from .tools import text_to_word_sequence, to_int, sort_suggestion
from .typo_distance import typo_distance
from .items import SuggestItem, DictionaryItem


def time_printer(func):
    def func_wrapper(*args, **kwargs):
        start_time = time.time()
        res = func(*args, *kwargs)
        print("--- {} executed in  {:.4f} s ---".format(func.__name__, time.time() - start_time))
        return res

    return func_wrapper


DISTANCE_MAPPER = {
    "dameraulevenshtein": damerau_levenshtein_distance,
    "typo": typo_distance
}


class SySpellCompound(object):
    def __init__(self, distance="dameraulevenshtein"):

        if not(distance in DISTANCE_MAPPER or callable(distance)):
            raise DistanceException("Distance must be dameraulevenshtein, typo or a function taking two arguments "
                                    "the two words which needs to be compared")

        self.enable_compound_check = True
        # false: assumes input string as single term, no compound splitting / decompounding
        # true:  supports compound splitting / decompounding with three cases:
        # 1. mistakenly inserted space into a correct word led to two incorrect terms
        # 2. mistakenly omitted space between two correct words led to one incorrect combined term
        # 3. multiple independent input terms with/without spelling errors
        self.edit_distance_max = 2
        self.verbose = 0  # //ALLWAYS use verbose = 0 if enableCompoundCheck = true!
        # 0: top suggestion
        # 1: all suggestions of smallest edit distance
        # 2: all suggestions <= editDistanceMax (slower, no early termination)

        #  //Dictionary that contains both the original words and the deletes derived from them. A term might be both word and delete from another word at the same time.
        # //For space reduction a item might be either of type dictionaryItem or Int.
        # //A dictionaryItem is used for word, word/delete, and delete with multiple suggestions. Int is used for deletes with a single suggestion (the majority of entries).
        # //A Dictionary with fixed value type (int) requires less memory than a Dictionary with variable value type (object)
        # //To support two types with a Dictionary with fixed type (int), positive number point to one list of type 1 (string), and negative numbers point to a secondary list of type 2 (dictionaryEntry)
        self.dictionary = {}  # Initialize
        self.word_list = []
        self.item_list = []
        self.max_length = 0

        # self.bigram = {} TODO: Remove it

    @staticmethod
    def parse_words(text):
        return text_to_word_sequence(text=text,
                                     filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n',
                                     lower=True,
                                     split=' ')

        # @time_printer

    def create_dictionary_entry(self, key, language, count):
        count_threshold = 1
        count_previous = 0
        result = False
        value = None
        valueo = self.dictionary.get(language + key, None)  # 117
        if value is not None:
            if valueo >= 0:  # 122
                tmp = valueo
                value = DictionaryItem()
                value.suggestions.append(tmp)  # value.suggestions.TrimExcess();
                self.item_list.append(value)
                self.dictionary[language + key] = -len(self.item_list)
            else:  # 131
                value = self.item_list[-valueo - 1]

            count_previous = value.count
            value.count += count
        else:  # 140
            # New word
            value = DictionaryItem()
            value.count = count
            self.item_list.append(value)
            self.dictionary[language + key] = -len(self.item_list)
            self.max_length = max(len(key), self.max_length)  # if (key.Length > maxlength) maxlength = key.Length;

        if value.count >= count_threshold > count_previous:  # 154
            self.word_list.append(key)
            keyint = len(self.word_list) - 1
            result = True

            for delete in self.edits(word=key, edit_distance=0, deletes=set()):  # 163
                value2 = self.dictionary.get(language + delete, None)
                if value2 is not None:
                    if value2 >= 0:
                        di = DictionaryItem()
                        di.suggestions.append(value2)
                        self.item_list.append(di)
                        self.dictionary[language + delete] = -len(self.item_list)
                        if keyint not in di.suggestions:  # 177
                            _ = self.add_lowest_distance(item=di, suggestion=key, suggestion_int=keyint, delete=delete)
                    else:
                        di = self.item_list[-value2 - 1]
                        if keyint not in di.suggestions:  # 182
                            _ = self.add_lowest_distance(item=di, suggestion=key, suggestion_int=keyint, delete=delete)
                else:
                    self.dictionary[language + delete] = keyint
        return result

    def load_dictionary(self, corpus, language, term_index, count_index):
        # path = os.path.join(__file__, corpus)
        path = corpus
        if not os.path.isfile(path=path): return False
        for line in SySpellCompound.load_file(path=path):
            tokens = text_to_word_sequence(line)
            if len(tokens) >= 2:
                key = tokens[term_index]
                count = to_int(tokens[count_index])
                if count:
                    self.create_dictionary_entry(key=key, language=language, count=count)

        return True

    def create_dictionary(self, corpus, language):
        # path = os.path.join(__file__, corpus)
        path = corpus
        if not os.path.isfile(path=path): return False
        for line in SySpellCompound.load_file(path=path):
            for token in line.split():
                self.create_dictionary_entry(key=token, language=language, count=1)

        return True

    @staticmethod
    def load_file(path):
        with open(path, 'r') as f:
            for line in f:
                yield line

    def add_lowest_distance(self, item, suggestion, suggestion_int, delete):
        if self.verbose < 2 and len(item.suggestions) > 0 and (
                len(self.word_list[item.suggestions[0]]) - len(delete)) > (len(suggestion) - len(delete)):
            item.suggestions.clear()

        if self.verbose == 2 or len(item.suggestions) == 0 or (
                    len(self.word_list[item.suggestions[0]]) - len(delete) >= len(suggestion) - len(delete)):
            item.suggestions.append(suggestion_int)
        return item

    def edits(self, word, edit_distance, deletes):
        edit_distance += 1
        if len(word) > 1:
            for index in range(0, len(word)):
                delete = word[:index] + word[index + 1:]
                if delete not in deletes:
                    deletes.add(delete)
                    if edit_distance < self.edit_distance_max:
                        self.edits(word=delete, edit_distance=edit_distance, deletes=deletes)
        return deletes

    def lookup(self, input_string, language, edit_distance_max):
        if len(input_string) - edit_distance_max > self.max_length:
            return []

        candidates = []
        hashset1 = set()
        suggestions = []
        hashset2 = set()

        candidates.append(input_string)

        while len(candidates) > 0:
            candidate = candidates[0]
            candidates.pop(0)

            if self.verbose < 2 and len(suggestions) > 0 and len(input_string) - len(candidate) > suggestions[
                0].distance:
                break  # 302

            valueo = self.dictionary.get(language + candidate, None)
            if valueo is not None:  # 305
                value = DictionaryItem()
                if valueo >= 0:  # 308
                    value.suggestions.append(int(valueo))
                else:
                    value = self.item_list[-valueo - 1]

                if value.count > 0 and candidate not in hashset2:  # 311
                    hashset2.add(candidate)
                    distance = len(input_string) - len(candidate)
                    if self.verbose == 2 or len(suggestions) == 0 or distance <= suggestions[0].distance:
                        if self.verbose < 2 and len(suggestions) > 0 and suggestions[0].distance > distance:
                            suggestions = []
                        si = SuggestItem()
                        si.term = candidate
                        si.count = value.count
                        si.distance = distance
                        suggestions.append(si)
                        # Early stopping
                        if self.verbose < 2 and (len(input_string) - len(candidate)) == 0:
                            break
                            #  333
                for suggestion_int in value.suggestions:
                    suggestion = self.word_list[suggestion_int]
                    if suggestion not in hashset2:
                        hashset2.add(suggestion)
                        distance = 0
                        if suggestion != input_string:

                            # Reviewed until heres
                            if len(suggestion) == len(candidate):
                                distance = len(input_string) - len(candidate)
                            elif len(input_string) == len(candidate):
                                distance = len(suggestion) - len(candidate)
                            else:
                                ii = 0
                                jj = 0
                                while ii < len(suggestion) and \
                                        ii < len(input_string) and \
                                        suggestion[ii] == input_string[ii]: ii += 1
                                while jj < len(suggestion) - ii and \
                                        jj < len(input_string) - ii and \
                                        suggestion[- jj - 1] == input_string[- jj - 1]: jj += 1

                                if ii > 0 or jj > 0:
                                    distance = distance_between_words(
                                        suggestion[ii:- ii - jj],
                                        input_string[ii: - ii - jj])
                                else:
                                    distance = distance_between_words(suggestion, input_string)
                        if self.verbose < 2 and len(suggestions) > 0 and distance > suggestions[0].distance: continue
                        if distance <= edit_distance_max:
                            value2 = self.dictionary.get(language + suggestion, None)
                            if value2 is not None:
                                si = SuggestItem()
                                si.term = suggestion
                                si.count = self.item_list[-value2 - 1].count
                                si.distance = distance

                                if self.verbose < 2 and len(suggestions) and suggestions[0].distance > distance:
                                    suggestions = []
                                suggestions.append(si)

                if len(input_string) - len(candidate) < edit_distance_max:
                    if self.verbose < 2 and \
                            len(suggestions) > 0 and \
                                len(input_string) - len(candidate) >= suggestions[0].distance:
                        continue

                    for index in range(0, len(candidate)):
                        delete = candidate[:index] + candidate[index + 1:]
                        if delete not in hashset1:
                            hashset1.add(delete)
                            candidates.append(delete)

        if self.verbose < 2:
            # sorted(suggestions, key=lambda x: x.count, reverse=True)
            suggestions = sort_suggestion(suggestions, fonction=lambda x: x.count)
        else:
            suggestions = sort_suggestion(suggestions, fonction=lambda x: 2 * x.distance - x.count)
            # sorted(suggestions, key=lambda x: 2 * x.distance - x.count, reverse=True)

        if self.verbose == 0 and len(suggestions) > 1:
            return suggestions[0:1]
        else:
            return suggestions

    # @time_printer
    def lookup_compound(self, input_string, language, edit_distance_max):

        term_list_1 = input_string.split()
        suggestions = []
        suggestion_parts = []

        last_combi = False

        for i in range(0, len(term_list_1)):
            suggestions_previous_term = []
            for k in range(0, len(suggestions)):
                suggestions_previous_term.append(copy(suggestions[k]))
            suggestions = self.lookup(input_string=term_list_1[i], language=language,
                                      edit_distance_max=edit_distance_max)
            if i > 0 and not last_combi:
                suggestions_combi = self.lookup(input_string=term_list_1[i - 1] + term_list_1[i],
                                                language=language,
                                                edit_distance_max=edit_distance_max)
                if len(suggestions_combi) > 0:
                    best1 = suggestion_parts[-1]
                    best2 = SuggestItem()
                    if len(suggestions) > 0:
                        best2 = suggestions[0]
                    else:
                        best2.term = term_list_1[i]
                        best2.distance = edit_distance_max + 1
                        best2.count = 0

                    if suggestions_combi[0].distance + 1 < distance_between_words(
                                term_list_1[i - 1] + " " + term_list_1[i], best1.term + " " + best2.term):
                        suggestions_combi[0].distance += 1
                        suggestion_parts[-1] = suggestions_combi[0]
                        last_combi = True
                        break
            last_combi = False

            if len(suggestions) > 0 and (suggestions[0].distance == 0 or len(term_list_1[i]) == 1):
                suggestion_parts.append(suggestions[0])
            else:
                suggestions_split = []
                if len(suggestions) > 0:  # 473
                    suggestions_split.append(suggestions[0])
                if len(term_list_1[i]) > 1:
                    for j in range(1, len(term_list_1[i])):
                        part1 = term_list_1[i][0:j]
                        part2 = term_list_1[i][j]
                        suggestion_split = SuggestItem()
                        suggestions1 = self.lookup(input_string=part1, language=language,
                                                   edit_distance_max=edit_distance_max)
                        if len(suggestions1) > 0:
                            if len(suggestions) > 0 and suggestions[0].term == suggestions1[0].term:
                                # if split correction1 == einzelwort correction
                                break
                            suggestions2 = self.lookup(input_string=part2, language=language,
                                                       edit_distance_max=edit_distance_max)
                            if len(suggestions1) > 0:
                                # if split correction1 == einzelwort correction
                                if len(suggestions) > 0 and suggestions[0].term == suggestions2[0].term:
                                    break
                                suggestion_split.term = suggestions1[0].term + " " + suggestions2[0].term
                                suggestion_split.distance = distance_between_words(term_list_1[i],
                                                                                   suggestions1[
                                                                                       0].term + " " +
                                                                                   suggestions2[
                                                                                       0].term)
                                suggestion_split.count = min(suggestions1[0].count, suggestions2[0].count)
                                suggestions_split.append(suggestion_split)
                                if suggestion_split.distance == 1:
                                    break
                    if len(suggestions_split) > 0:
                        # sorted(suggestions_split, key=lambda x: 2 * x.distance - x.count, reverse=True)
                        suggestions_split = sort_suggestion(suggestions_split,
                                                            fonction=lambda x: 2 * x.distance - x.count)
                        suggestion_parts.append(suggestions_split[0])
                    else:
                        si = SuggestItem()
                        si.term = term_list_1[i]
                        si.count = 0
                        si.distance = edit_distance_max + 1
                        suggestion_parts.append(si)

                else:
                    si = SuggestItem()
                    si.term = term_list_1[i]
                    si.count = 0
                    si.distance = edit_distance_max + 1
                    suggestion_parts.append(si)

        suggestion = SuggestItem()
        suggestion.count = math.inf
        s = ""
        for si in suggestion_parts:
            s += si.term + " "
            suggestion.count = min(si.count, suggestion.count)
        suggestion.term = s.strip()
        suggestion.distance = distance_between_words(suggestion.term, input_string)

        # suggestions_line = [suggestion]
        # return suggestions_line
        return suggestion


def distance_between_words(word1, word2):
    return damerau_levenshtein_distance(word1, word2)
    # return typo_distance(s=word1, t=word2, layout='AZERTY')


if __name__ == "__main__":
    ssc = SySpellCompound()
    print(ssc.load_dictionary("fr_full.txt", language="fr", term_index=0, count_index=1))
    print(ssc.dictionary.get("frprobleme"))
    # print(ssc.create_dictionary("model_fr.txt", "fr"))

    print(ssc.lookup_compound(input_string="le problm avc cete solutin", language="fr", edit_distance_max=3))
