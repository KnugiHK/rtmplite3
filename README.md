# What is rtmplite? #
More details in [rtmplite](/rtmplite.md)

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

* master: main branch; stable
* dev: development branch; maybe buggy
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

Typically an application can launch this server as follows:
```
$ python rtmp.py -d
```
The -d option enables debug trace so you know what is happening in the server. **Please note that debug trace will hugely affect the performance of the RTMP server**

To know the command line options use the -h option:
```
$ python rtmp.py -h
```
For your convenience, this repo also provide you a single executable. You may want to check out our [release page](https://github.com/KnugiHK/rtmplite3/releases).

And here is how to use the executable
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

