from setuptools import setup, find_packages

setup(
    name='nhl_linemate_scraper',
    version='0.1.0',
    author='Stats By Zach',
    author_email='ztandrews18@sbcglobal.net',
    description='A Python package for scraping NHL linemate data',
    long_description=open('README.md').read(),
    long_description_content_type='markdown',
    url='https://github.com/ztandrews/nhl-linemate-scraper',
    packages=find_packages(exclude=['tests*','examples*']),
    install_requires=[
        'beautifulsoup4>4.0',
        'numpy>1.0',
        'pandas>2.0',
        'requests>2.0'
    ],
    python_requires='>=3.6',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

