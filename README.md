# What is rtmplite? #
More details in [rtmplite](/rtmplite.md) and [siprtmp](/siprtmp.md)

> This project was migrated from <https://code.google.com/p/rtmplite> on May 17, 2015  
> Additionally the documentation from <https://code.google.com/p/siprtmp> was merged on May 17, 2015  
> Please see these individual description files for [rtmplite](/rtmplite.md) or [siprtmp](/siprtmp.md)  

# Copyright #

Copyright (c) 2007-2009, Mamta Singh.  
Copyright (c) 2010-2011, Kundan Singh. All rights reserved.  
Copyright (c) 2011-2012, Intencity Cloud Technologies. All rights reserved.  
Copyright (c) 2011, Cumulus Python. No rights reserved.  

See [contributors](/people.png).

# Upgrade from the original repo
This repo aims to upgrade the original repo from Python 2 to Python 3, as well as integrate into my [self-host video streaming project](https://github.com/KnugiHK/video-streaming). Therefore, only rtmp.py and its dependencies will be modified in this repo.

## Why am I doing this
I am working on a [self-host video streaming](https://github.com/KnugiHK/video-streaming) project with Python 3 and Flask, hence, I need a Python 3 RTMP server. However, most of the Python RTMP solution do not match what I need (developed using Python 2, no longer maintained etc.), so, I decided to transit a Python 2 solution to Python 3.

# Branches
This repo has three branches including master, dev and svs (self-host streaming).

* master: main branch; stable
* dev: development branch; maybe buggy
* svs: customized branch for self-host video streaming project

# RTMP server #

The main program is rtmp.py. Please see the embedded documentation in that file.
Some parts of the documentation are copied here. Other modules such as amf, util
and multitask are used from elsewhere and contain their respective copyright 
notices.

# Getting Started #

Dependencies: Python 3.6+ (Perhaps)
Tested environment: Windows 10 1909 with Python 3.8.3rc1

Typically an application can launch this server as follows:
```
$ python rtmp.py -d
```
The -d option enables debug trace so you know what is happening in the server. **Please note that debug trace will hugely affect the performance of the RTMP server**

To know the command line options use the -h option:
```
$ python rtmp.py -h
```
