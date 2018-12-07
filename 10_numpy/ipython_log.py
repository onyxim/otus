# IPython log file

get_ipython().run_cell_magic(u'quickref', u'', u'')
get_ipython().magic(u'quickref')
b = [1, 2, 3]
get_ipython().magic(u'pinfo b')
b = [1, 2, 3]
get_ipython().magic(u'pinfo b')
get_ipython().magic(u'pinfo str.split')
get_ipython().magic(u'pinfo2 str.split')
def gcd(a, b):
    """Computes the greatest common divisor of integers a and b using
    Euclid's Algorithm.
    """
    while True:
        if b == 0:
            return a
        a, b = b, a % b
get_ipython().magic(u'pinfo gcd')
import uuid
get_ipython().magic(u'pinfo2 uuid.uuid4')
get_ipython().magic(u'pinfo str.split')
get_ipython().magic(u'psearch str.*split*')
get_ipython().magic(u'run gcd.py')
print a, b
get_ipython().magic(u'run gcd.py')
import numpy as np
a = np.random.randn(100, 100)
a = np.random.randn(100, 100)
get_ipython().magic(u'timeit np.dot(a, a)')
get_ipython().magic(u'pinfo %reset')
'a' in _ip.user_ns
get_ipython().magic(u'magic')
print _
get_ipython().magic(u'run gcd.py')
print _
get_ipython().magic(u'run gcd.py')
print _
get_ipython().magic(u'run gcd.py')
get_ipython().magic(u'run gcd.py')
366*31*24*60*60
print _
_ * 10
366*31*24*60*60
_ * 2
print _, __
two_years_sec = 980294400
print _i34, _34
two_years_sec = 980294400
two_years_sec
print _i36, _36
print _i36
print _i36
print _36
exec _i36
get_ipython().magic(u'hist')
get_ipython().magic(u'logstart')
get_ipython().magic(u'logoff')
