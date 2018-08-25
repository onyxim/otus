#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------
# Реализуйте функцию best_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. У каждой карты есть масть(suit) и
# ранг(rank)
# Масти: трефы(clubs, C), пики(spades, S), червы(hearts, H), бубны(diamonds, D)
# Ранги: 2, 3, 4, 5, 6, 7, 8, 9, 10 (ten, T), валет (jack, J), дама (queen, Q), король (king, K), туз (ace, A)
# Например: AS - туз пик (ace of spades), TH - дестяка черв (ten of hearts), 3C - тройка треф (three of clubs)

# Задание со *
# Реализуйте функцию best_wild_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. Кроме прочего в данном варианте "рука"
# может включать джокера. Джокеры могут заменить карту любой
# масти и ранга того же цвета, в колоде два джокерва.
# Черный джокер '?B' может быть использован в качестве треф
# или пик любого ранга, красный джокер '?R' - в качестве черв и бубен
# любого ранга.

# Одна функция уже реализована, сигнатуры и описания других даны.
# Вам наверняка пригодится itertoolsю
# Можно свободно определять свои функции и т.п.
# -----------------
from enum import Enum
from itertools import combinations, groupby, tee, product


# В задании вроде это не указано или указано неявно. (Кстати, задание написано не очень понятно, доработать бы) Решил
#  определять силу руки по разрядно в сторичной системе исчисления. Разряды задаются первым числом. Под
# некоторые комбинации выделено 2-3 разряда, потому как для определения старшинства может требоваться больше карт.
def hand_rank(hand):
    """Возвращает значение определяющее ранг 'руки'"""
    # Думаю, что можно было бы всю эту case гребенку завернуть в dict, но сохранил структуру оригинала
    ranks = card_ranks(hand)
    if straight(ranks) and flush(hand):
        return 13, ranks[0]
    elif kind(4, ranks):
        return 12, kind(4, ranks)[0]
    elif kind(3, ranks) and kind(2, ranks):
        # [0] на вызовах функции, потому что оставшееся самое большое число на не нужно.
        return 10, kind(3, ranks)[0], kind(2, ranks)[0]
    elif flush(hand):
        return 9, sum(ranks)  # вот именно из-за этого на сторичную систему перешел
    elif straight(ranks):
        return 8, ranks[0]
    elif kind(3, ranks):
        return (6,) + kind(3, ranks)
    elif two_pair(ranks):
        return (3,) + two_pair(ranks)  # вернется 3 значения
    elif kind(2, ranks):
        return (1,) + kind(2, ranks)
    else:
        return 0, ranks[0]


class Ranks(Enum):
    T = 10
    J = 11
    Q = 12
    K = 13
    A = 14


# Основание для системы исчесления использующийся для высчитания очков за руку
RANK_BASE = 100

SUITS_JOKER = {
    '?B': 'SC',
    '?R': 'HD',
}


def try_int(v, reverse=False):
    try:
        if reverse:
            return Ranks(v).name
        else:
            return Ranks[v].value
    except (KeyError, ValueError):
        return int(v)


# Может быть есть более эффективный и лаконичный способ это сделать? Пока не придумал. На itertools так на itertools.
def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


# Стартовая комбинация из 7 карт предварительно сортируется от большего к меньшему, поэтому достаточно просто сделать
#  list comprehension
def card_ranks(hand):
    """Возвращает список рангов (его числовой эквивалент),
    отсортированный от большего к меньшему"""
    # Необходимость существования данной функции вызывают сомнение, потому как при первичной
    return [try_int(v[0]) for v in hand]


def flush(hand):
    """Возвращает True, если все карты одной масти"""
    g = groupby(hand, key=lambda v: v[1])
    return next(g, True) and not next(g, False)


# Я не мастер игры в покер, вроде на flush straight последовательность может через туз начинаться с двойки. Я такой
# вариант не учитывал, хотя могу, если нужно.
def straight(ranks):
    """Возвращает True, если отсортированные ранги формируют последовательность 5ти,
    где у 5ти карт ранги идут по порядку (стрит)"""
    for x, y in pairwise(ranks):
        if x - y != 1:
            return False
    return True


# Можно, кстати, что-то вроде кэша сделать, чтобы для одинаковых комбинаций не считать одно и то же.
def kind(n, ranks):
    """Возвращает первый ранг, который n раз встречается в данной руке.
    Возвращает None, если ничего не найдено"""
    kick = None
    result = None
    for k, g in groupby(ranks):
        g_list = list(g)
        if len(g_list) == 1 and not kick:
            kick = k
        elif len(g_list) == n and not result:
            result = k
    if result:
        return result, kick


def two_pair(ranks):
    """Если есть две пары, то возврщает два соответствующих ранга,
    иначе возвращает None"""
    kick = None
    max_pair = None
    low_pair = None
    for k, g in groupby(ranks):
        g_list = list(g)
        if len(g_list) == 1 and not kick:
            kick = k
        elif len(g_list) == 2:
            # Список на входе отсортирован, ничего сранивать дополнительно не приходится
            if not max_pair:
                max_pair = k
            else:
                low_pair = k
    if max_pair and low_pair:
        return max_pair, low_pair, kick


def calc_score(result):
    """В функцию поступает tuple в котором первую позицию занимает стартовы разряд, который нужно прибавить в начале,
     а далее значения следующих разрядов в 100-ричной системе. На выходе получается десятичное натуральное число,
     характеризующее силу руки."""
    # сумму за предыдущие разряды
    sum_ = result[0] * RANK_BASE
    # reversed, так как значения из hand_rank передаются в порядке убывания разрядов
    for n, v in enumerate(reversed(result[1:])):
        # В принципе можно обойтись без обратной кодировки в str, но пусть будет так.
        sum_ = sum_ + (RANK_BASE * n) + v
    return sum_


def best_hand(hand, sorted_result=True, split_input=True, return_max_score=False):
    """Из "руки" в 7 карт возвращает лучшую "руку" в 5 карт """
    hand = hand.split() if split_input else hand
    hand = sorted(hand, key=lambda k: try_int(k[0]), reverse=True)
    max_score = 0
    _best_hand = ''
    for hand_5 in combinations(hand, 5):
        result = hand_rank(hand_5)
        score = calc_score(result)
        if score > max_score:
            max_score = score
            _best_hand = hand_5

    if sorted_result:
        _best_hand = sorted(_best_hand)
    if return_max_score:
        return _best_hand, max_score
    return _best_hand


def cards_generator(suits):
    for rank, suit in product(range(2, 15), suits):
        yield str(try_int(rank, reverse=True)) + suit


def best_wild_hand(hand, split_input=True):
    """best_hand но с джокерами"""
    hand = hand.split() if split_input else hand
    joker_suits = []
    max_score = 0
    _best_hand = ''
    for joker in SUITS_JOKER.keys():
        try:
            index = hand.index(joker)
        except ValueError:
            continue
        hand.pop(index)
        joker_suits.append(cards_generator(SUITS_JOKER[joker]))
    stable_hand = tuple(hand)
    for cards_set in product(*joker_suits):
        hand = stable_hand + cards_set
        hand, score = best_hand(hand, split_input=False, return_max_score=True)
        if score > max_score:
            max_score = score
            _best_hand = hand
    return _best_hand


def test_best_hand():
    print("test_best_hand...")
    assert best_hand("6C 7C 8C 9C TC 5C JS") == ['6C', '7C', '8C', '9C', 'TC']
    assert best_hand("TD TC TH 7C 7D 8C 8S") == ['8C', '8S', 'TC', 'TD', 'TH']
    assert best_hand("JD TC TH 7C 7D 7S 7H") == ['7C', '7D', '7H', '7S', 'JD']
    print('OK')


def test_best_wild_hand():
    print("test_best_wild_hand...")
    assert best_wild_hand("6C 7C 8C 9C TC 5C ?B") == ['7C', '8C', '9C', 'JC', 'TC']
    assert best_wild_hand("TD TC 5H 5C 7C ?R ?B") == ['7C', 'TC', 'TD', 'TH', 'TS']
    assert best_wild_hand("JD TC TH 7C 7D 7S 7H") == ['7C', '7D', '7H', '7S', 'JD']
    print('OK')


if __name__ == '__main__':
    test_best_hand()
    test_best_wild_hand()
