import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

# Package Meta-Data
NAME = "instascrape-ax"
DESCRIPTION = "A fast and lightweight Instagram media downloader"
URL = "https://github.com/a1phat0ny/InstaScrape"
EMAIL = "tony.chan2342@gmail.com"
AUTHOR = "a1phat0ny"
REQUIRES_PYTHON = ">=3.6.0"
REQUIRED = [
    "requests",
    "tqdm",
    "colorama"
]
about = {}
with open(os.path.join(here, "instascrape", "__version__.py"), "r") as f:
    exec(f.read(), about)

long_description = \
"""
InstaScrape is a lightweight command-line utility for downloading large amount of photos and videos from Instagram in bulk.

## Features

* Fancy output with colors ✨
* Fast as lightning,️ with multithreaded scraping support ⚡
* Efficient, use generators (yield) 💪🏻
* Yield data to prevent getting rate limited by Instagram
* Manage cookies and multiple accounts easily 🍪
* Download posts along with their metadata
* Job queue to handle multiple download tasks 🏃🏻‍
* Good exceptions handling ⚠️
* Download posts created in a particular time period 🕓
* Download large amount of media at once
* Detect and Skip existing files automatically to avoid re-downloading
* Simple to use API
* Simple to use CLI (use symbols)
"""

# Setup
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    entry_points={
        "console_scripts": ["instascrape=instascrape.cli:main"],
    },
    install_requires=REQUIRED,
    include_package_data=True,
    packages=find_packages(),
    license="MIT",
    keywords=["instagram", "scraper", "api", "downloader", "media", "cli"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy"
    ],
)
