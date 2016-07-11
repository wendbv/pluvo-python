from distutils.core import setup


setup(
    name='pluvo',
    packages=['pluvo'],
    package_data={},
    version='0.1.0b1',
    description='Python library to access the Pluvo REST API.',
    author='Daan Porru (Wend)',
    author_email='daan@wend.nl',
    license='MIT',
    url='https://github.com/wendbv/pluv-python',
    keywords=['REST', 'API', 'Pluvo'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    install_requires=["coverage", "pytest", "pytest-cov", "pytest-flake8",
                      "pytest-mock", "requests"],
)
