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
This repo aims to upgrade the original repo from Python 2 to Python 3, as well as integrate into my [self-host video streaming project](https://github.com/KnugiHK/video-streaming). Therefore, only rtmp.py will be modified in this repo.

# RTMP server #

The main program is rtmp.py. Please see the embedded documentation in that file.
Some parts of the documentation are copied here. Other modules such as amf, util
and multitask are used from elsewhere and contain their respective copyright 
notices.

# Getting Started #

Dependencies: Python 3.8

Typically an application can launch this server as follows:
```
$ python rtmp.py -d
```
The -d option enables debug trace so you know what is happening in the server. **Please note that debug trace will hugely affect the performance of the RTMP server**

To know the command line options use the -h option:
```
$ python rtmp.py -h
```
