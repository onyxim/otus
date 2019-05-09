from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy as np

setup(
    cmdclass={'build_ext': build_ext},
    ext_modules=[Extension(
        "calculate",
        sources=["cythonfn_mp.pyx"],
        extra_compile_args=["-w", "-fopenmp"],
        extra_link_args=["-fopenmp"],
        include_dirs=[np.get_include()])
    ],
)
