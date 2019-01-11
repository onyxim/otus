# Пояснения по заданию

## 1 Новый opcode LOAD_OTUS

Изначально попробовал добавить свой opcode в python 3.7.2, но не получилось собрать python c внесенными изменениями. (тем не менее патч представил в репозитории) Тогда решил модифицировать 2.7.15.

После успешной сборки интерпретатора произвел замеры скорости работы (модуль 1_opcode_fib_test.py), результаты такие:
1. 2.19918680191 for Python 2.7.15 vanilla
2. 1.71803498268 for Python 2.7.15 with new LOAD_OTUS opcode

То есть, интерпретатор python с новым опкодом LOAD_OTUS однозначно быстрее примерно на 1.28 раза чем ванильный интерпретатор.

### ошибка при сборке с python 3.7.2

make валится с такой ошибкой:
```bash
/bin/sh: line 5: 18389 Segmentation fault      (core dumped) ./python -E -S -m sysconfig --generate-posix-vars
generate-posix-vars failed
make: *** [Makefile:604: pybuilddir.txt] Error 1
```

Смотрел в dump, победить не удалось, увы. Скорее всего недостаточно опыта разработки на `C`.

### Как юзать make для сборки грамматики и ast

make regen-grammar
make regen-ast

## 2 реализация until

С этим все ок.

## 3 increment_decrement

Не смог одолеть `forbidden_name` - нет такой функции мне сообщают компилятор. Возможно, это `forbidden_check` сейчас? Но не понятно.


