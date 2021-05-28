import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rtmplite3",
    version="0.3.5",
    author="KnugiHK",
    author_email="info@knugi.com",
    description="Maybe this is the first RTMP server in Python 3",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/KnugiHK/rtmplite3",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts':[
            'rtmplite3 = rtmplite3.__main__:main'
        ],
    }
)