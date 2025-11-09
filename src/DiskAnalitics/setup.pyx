from setuptools import setup, Extension
from Cython.Build import cythonize

setup(
    name="libdiscscan",
    ext_modules=cythonize(
        [Extension("libdiskscan", ["libdiskscan.pyx"])],
        language_level=3,
    ),
    zip_safe=False,
)
