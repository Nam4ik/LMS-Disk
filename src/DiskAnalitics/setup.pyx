from setuptools import setup
from Cython.Build import cythonize

setup(
    name='disk_analyzer',
    ext_modules=cythonize(["Disk.pyx"], language_level=3),
    zip_safe=False,
)

