# RTMPLite3 #
[![Latest version released on PyPi](https://img.shields.io/pypi/v/rtmplite3.svg?style=flat&label=latest%20version)](https://pypi.org/project/rtmplite3/) ![Master Testing](https://github.com/KnugiHK/rtmplite3/workflows/Master%20testing/badge.svg)

This repo is part of [self-host video streaming project](https://github.com/users/KnugiHK/projects/3).

No major new function designated for RTMP server will be introduced, since the original author has updated the RTMPlite project. However, bugs and features required by the self-host video streaming project will still be fixed and developed. [Link to the repo created by original author.](https://github.com/theintencity/rtclite/tree/python3)

# What is rtmplite3? #
This is a fork of rtmplite with conversion of Python 2 to Python 3
More details in [rtmplite](https://github.com/KnugiHK/rtmplite3/wiki/rtmplite)

> This project was migrated from <https://code.google.com/p/rtmplite> on May 17, 2015  
> Please see these individual description files for [rtmplite](/rtmplite.md)

# Copyright #

Copyright (c) 2007-2009, Mamta Singh.  
Copyright (c) 2010-2011, Kundan Singh. All rights reserved.  
Copyright (c) 2011-2012, Intencity Cloud Technologies. All rights reserved.  
Copyright (c) 2011, Cumulus Python. No rights reserved.  

See [contributors](/people.png).

# Upgrade from the original repo #
This repo aims to upgrade the original repo from Python 2 to Python 3, as well as integrate into my [self-host video streaming project](https://github.com/KnugiHK/video-streaming). Therefore, only rtmp.py and its dependencies will be modified in this repo.

## Why am I doing this ##
I am working on a [self-host video streaming](https://github.com/KnugiHK/video-streaming) project with Python 3 and Flask, hence, I need a Python 3 RTMP server. However, most of the Python RTMP solution do not match what I need (developed using Python 2, no longer maintained etc.), so, I decided to transit a Python 2 solution to Python 3.

# Branches #
This repo has three branches including master, dev and svs (self-host streaming).

* master: release branch; stable
* dev: development branch; maybe buggy or even can't run at all
* svs: customized branch for self-host video streaming project

# RTMP server #

The main program is rtmp.py. Please see the embedded documentation in that file.
Some parts of the documentation are copied here. Other modules such as amf, util
and multitask are used from elsewhere and contain their respective copyright 
notices.

## Documentation ##
Instead of looking at the documentation from the source code, I migrated (or migrating) the embedded documentation from the source code to [Wiki of this repo](https://github.com/KnugiHK/rtmplite3/wiki).

# Getting Started #

Dependencies: Python 3.6+

Tested environment:
* Windows 10 1803 with Python 3.8.3rc1
* Ubuntu 18.04.4 LTS with Python 3.6.9.

First, clone all source files from this repo or install rtmplite3 from pip:
```shell
# Download from this repo
git clone https://github.com/KnugiHK/rtmplite3.git

# Install from pip
pip install rtmplite3
```
**There are multiple methods for you to run the RTMP server directly**

1. If you install the latest version (0.2.5) from pip, you can now start the RTMP server with the following methods:
```Shell
$ rtmplite3 -d #or
$ python -m rtmplite3 -d
```

2. Typically, an application can launch this server as follows if you clone this repo instead of install from pip:
```Shell
$ python rtmp.py -d
```
The -d option enables debug trace so you know what is happening in the server. 

There is also a -v option which enables verbose mode so you know all data sent and received in Hex. **Please note that verbose mode will hugely affect the performance of the RTMP server**

To know the command line options use the -h option:
```
$ python rtmp.py -h
```
For your convenience, this repo also provide you a single executable. You may want to check out our [release page](https://github.com/KnugiHK/rtmplite3/releases).

3. And here is how to use the executable
```Shell
# in Linux
$ chmod +x rtmp-Linux
$ ./rtmp-Linux

:: in Windows
> rtmp-Windows.exe
or double click the file
```

# Known issues
1. The program cannot exit with Control+C in Windows
2. Viewer cannot join the stream after the feed started to broadcast
3. recording and verbose mode will not enable when run with direct command and run as Python module

# Contribution #
If you want to help me to improve the quality of this project, you can submit an issue.

If you want to collaborate with us, feel free to Fork this project and open a pull request.

### What can you do? ###

* For Issue
  * Report any Logical Error.
  * Report any Run-Time Error.
  * Request new features
  * Ask questions if you do not understand something.

* For Pull request
  * Add comments to source code.
  * Add new features
  * Correct any Logical Error.
  * Correct any Run-Time Error.

