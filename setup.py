import pathlib
from setuptools import setup

VERSION = '0.1.4'
README = (pathlib.Path(__file__).parent / 'README.md').read_text()

setup(
    name='dcgoss',
    version=VERSION,
    author='Shelby Allen-Franks',
    author_email='shelby.allen@me.com',
    url='https://github.com/shelbyallenfranks/dcgoss',
    license='Apache License 2.0',
    description='A Python implementation of dcgoss',
    long_description=README,
    long_description_content_type='text/markdown',
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Testing'
    ],
    python_requires='>=3.6',
    install_requires=[
        'python-dateutil~=2.8.0'
    ],
    extras_require={
        ':sys_platform == "win32"': ['colorama>=0.4,<1.0']
    },
    packages=['dcgoss'],
    entry_points={
        'console_scripts': [
            'dcgoss=dcgoss.__main__:main'
        ]
    }
)
