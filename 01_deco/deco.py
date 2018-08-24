#!/usr/bin/env python
from functools import update_wrapper, partial, WRAPPER_ASSIGNMENTS
from itertools import zip_longest, chain


def get_global_func(func):
    r = globals()[func.__name__]
    if r.__module__ != func.__module__:
        raise ValueError('Wrong decorated func name!')
    return r


# В итоге пришлось добавить в каждый декоратор код, чтобы реализовать disable как описано. Может быть есть другой,
# более изящный способ?
def disable():
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable

    '''
    pass


CUSTOM_WRAPPER_ASSIGNMENTS = WRAPPER_ASSIGNMENTS + ('calls',)


# Здесь я не совсем понял, требовалось изобрести свой декоратор wraps? Или что-то другое? Нужно пояснение.
def decorator(func):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''

    return partial(update_wrapper, wrapped=func, assigned=CUSTOM_WRAPPER_ASSIGNMENTS)


class CountObj:

    def __init__(self):
        self.calls = 0

    def __repr__(self):
        return str(self.calls)


# В таком варианте цепочка вызовов может быть прервана декоратором без переноса .calls на обертку
def countcalls(func):
    '''Decorator that counts calls made to the function decorated.'''

    @decorator(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if countcalls.__name__ == disable.__name__:
            return result
        wrapper.calls.calls += 1
        return result

    wrapper.calls = CountObj()
    return wrapper


def countcalls2(func):
    '''Decorator that counts calls made to the function decorated.'''

    @decorator(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if countcalls.__name__ == disable.__name__:
            return result
        global_func = get_global_func(func)
        if hasattr(global_func, 'calls'):
            global_func.calls += 1
        else:
            global_func.calls = 1
        return result

    return wrapper


def memo(func):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    cache_dict = {}

    @decorator(func)
    def wrapper(*args, **kwargs):
        if memo.__name__ == disable.__name__:
            func(*args, **kwargs)
        cache = cache_dict.get(args)
        if cache:
            return cache
        else:
            cache = func(*args, **kwargs)
            cache_dict[args] = cache
            return cache

    return wrapper


def n_ary(func):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''

    @decorator(func)
    def wrapper(*args, **kwargs):
        global_func = get_global_func(func)
        if len(args) <= 2 or n_ary.__name__ == disable.__name__:
            return func(*args, **kwargs)
        # Чтобы посчитать каждый вызов в рекурсии вызываем глобальную функцию,
        # а можно еще вот так :-) reduce(func, reversed(args))
        # но так мне меньше нравится чем написано в итоге
        return global_func(*args[:-2], global_func(*args[-2:], **kwargs), **kwargs)

    return wrapper


DIRECTION = {
    1: ' --> ',
    -1: ' <-- ',
}


def print_step(f, steps_data, delimiter, step, result, args, kwargs):
    """

    :param f_name:
    :param steps_data:
    :param step: может быть либо минус единицой, если мы идем вверх либо +1 если вниз
    :return:
    """
    f_name = f.__name__
    if step == -1:
        steps_data[f_name] += step
    step_print_list = [steps_data.setdefault(f_name, 0) * delimiter, DIRECTION[step], f_name, '(']
    args_kwargs_print = []
    iter_args = zip_longest([], args, fillvalue=None)
    # Да, я знаю что в данном случае kwargs не нужны, но я представил, что было бы если...
    for key, value in chain(iter_args, kwargs.items()):
        if args_kwargs_print:
            # Если в списке на вывод уже есть что либо, добавляем запятую перед следующим параметром
            args_kwargs_print.append(', ')
        if key:
            args_kwargs_print.extend((key, '=', value))
        else:
            args_kwargs_print.append(value)
    step_print_list.extend(args_kwargs_print)
    step_print_list.append(')')
    if result:
        step_print_list.extend((' == ', result))
    if step == 1:
        steps_data[f_name] += step
    print(*step_print_list, sep='')


def trace(delimiter):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''

    def decorate(func):
        steps_data = {}

        @decorator(func)
        def wrapper(*args, **kwargs):
            if trace.__name__ == disable.__name__:
                return func(*args, **kwargs)
            print_step(func, steps_data, delimiter, 1, None, args, kwargs)
            r = func(*args, **kwargs)
            print_step(func, steps_data, delimiter, -1, r, args, kwargs)
            return r

        return wrapper

    return decorate


@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n - 1) + fib(n - 2)


def main():
    print(foo(4, 3))
    print(foo(4, 3, 2))
    print(foo(4, 3))
    print("foo was called", foo.calls, "times")

    print(bar(4, 3))
    print(bar(4, 3, 2))
    print(bar(4, 3, 2, 1))
    print("bar was called", bar.calls, "times")

    print(fib.__doc__)
    fib(3)
    print(fib.calls, 'calls made')


if __name__ == '__main__':
    main()
