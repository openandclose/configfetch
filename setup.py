
"""configfetch setup file."""

# from setuptools import setup, find_packages
from setuptools import setup

with open('README.rst') as f:
    readme = f.read()

with open('VERSION') as f:
    version = f.read().strip()


setup(
    name='configfetch',
    version=version,
    url='https://github.com/openandclose/configfetch',
    license='MIT',
    author='Open Close',
    author_email='openandclose23@gmail.com',
    description='Helper to get values from configparser and argparse',
    long_description=readme,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Utilities',
    ],
    keywords='commandline configparser argparse',
    # packages=find_packages(exclude=['tests', 'nonpubfiles']),
    py_modules=['configfetch'],
    python_requires='~=3.6',
    extras_require={
        'test': ['lxml', 'pytest'],
        'dev': ['lxml', 'pytest', 'sphinx'],
    },
    zip_safe=False,
)
