func = "def fib(n): return fib(n - 1) + fib(n - 2) if n > 1 else n"
exec(func)

import dis

dis.dis(fib)

import timeit

print(timeit.timeit(stmt='fib(15)', setup=func, number=10000))

# 2.19918680191 for Python 2.7.15 vanilla

# 1.71803498268 for Python 2.7.15 with new LOAD_OTUS opcode
