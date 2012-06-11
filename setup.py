import glob
import re
from setuptools import setup


version = re.search("__version__ = '([^']+)'",
                    open('kurt/__init__.py').read()).group(1)


setup(name='kurt',
      author='Tim Radvan',
      author_email='blob8108@gmail.com',
      description='A library for reading/writing MIT Scratch files.',
      install_requires=['construct', 'pypng'],
      keywords=['scratch'],
      license='LGPL',
      packages=['kurt'],
      scripts=glob.glob('util/*'),
      url='https://github.com/blob8108/kurt',
      version=version
)
