from setuptools import setup


setup(
    name='pluvo',
    packages=['pluvo'],
    package_data={},
    version='0.2.9',
    description='Python library to access the Pluvo REST API.',
    author='Wend BV',
    author_email='info@wend.nl',
    license='MIT',
    url='https://github.com/wendbv/pluvo-python',
    keywords=['REST', 'API', 'Pluvo'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    install_requires=['requests'],
    tests_require=['coverage', 'flake8==2.6.2', 'pytest>=2.7', 'pytest-cov',
                   'pytest-flake8==0.2', 'pytest-mock']
)
