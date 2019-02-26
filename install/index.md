---
title: Installation
---

{% include dev-warning.html %}
{% include contents-float.html %}

_**Note:**  Currently, Linux is the only supported operating system._

Contents
--------

* [Running images](#running)
* [Building images](#building)
    * [Requirements](#requirements)
    * [Setup](#setup)


Running Images
--------------

The only thing you need to run an Elements container image is a Linux
distribution with `runc` installed.

Once you have `runc` installed, simply make the image executable and
run it.


Building images
---------------

### Requirements

**For building Elements containers,** you'll need **root privileges** and
the following items on the root user's $PATH:

* Python 3
* [Singularity](https://www.sylabs.io/singularity/)
* [appimagetool](https://github.com/AppImage/AppImageKit/releases)


**For building Elements itself,** you'll need:

* Git
* GNU make
* mypy for Python 3 (must be on the build user's $PATH)


### Setup

1.  Install the [requirements listed above](#requirements).

2.  Clone the Git repository:

    $ git clone https://gitlab.com/scottywz/elements.git

3.  Run `make` from the repository root.  The compiled version of Elements
    will be called `elements` in the repository root.
