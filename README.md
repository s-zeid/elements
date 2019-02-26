[Elements](https://www.youtube.com/watch?v=N0ziDSLJhq4)
=======================================================

A tool to generate single-file, runc-based AppImage containers.

Copyright (c) 2019 S. Zeid.  Some rights reserved under the X11 License.

<https://elements.s.zeid.me/>

**WARNING:**  Elements is not ready for production.  It is an experiment
in the early stages of development.  Although I make a best effort to not
commit broken code, there is no automated testing, there may be breaking
changes in future commits, there may be security or data loss bugs, and
there is no guarantee of long-term maintenance.  As the license states,
use at your own risk.  :)

*                        *                        *                        *

Elements is a tool to generate runc-based containers which are self-contained
in a single AppImage file.  The definition file can be used to specify if
and how parameters such as bind mounts and environment variables are passed
as arguments to the container's AppImage.

Elements uses an extended version of [Singularity Definition Files][sdf]
to define containers and has a container build-time dependency on Singularity.
(This is because I like the syntax better than that of Dockerfiles, but I
am open to adding support for Dockerfiles in the future.)  Singularity is
not used to run Elements containers, and unlike Singularity, **filesystems,
PID and IPC namespaces, and the environment ARE contained by default**.

At build time, Elements creates a POSIX-compliant (portable) shell script
which is shipped in the AppImage.  This script parses the user-supplied
arguments and constructs, runs, and tears down the underlying runc container
at a temporary path.  At present, this script relies on a minimal (~3 MB
compressed) Alpine Linux rootfs, which is generated at container build time,
is included in the AppImage, and contains jq for the purpose of configuring
runc.

There are no plans to rewrite Elements or the loader script in Go.  The
choice of Python and POSIX shell was intentional; however, I would like to
move some performance-sensitive loader code to a compiled language other
than Go in the future (this would allow getting rid of the bootstrap
filesystem).


[sdf]: https://www.sylabs.io/guides/3.0/user-guide/definition_files.html


## [Documentation](https://elements.s.zeid.me/)
