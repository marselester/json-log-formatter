from distutils.core import setup

setup(
    name='JSON-log-formatter',
    version='0.5.0',
    license='MIT',
    packages=['json_log_formatter'],
    author='Marsel Mavletkulov',
    author_email='marselester@ya.ru',
    url='https://github.com/marselester/json-log-formatter',
    description='JSON log formatter',
    long_description=open('README.rst').read(),
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
