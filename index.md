---
---

[**Elements**](https://www.youtube.com/watch?v=N0ziDSLJhq4)
is a tool to generate runc-based containers which are self-contained
in a single AppImage file.  The definition file can be used to specify if
and how parameters such as bind mounts and environment variables are passed
as arguments to the container's AppImage.


Current limitations
-------------------

Please see [the "Current limitations" section][limitations] of the README
file for some important notes about the current implementation.  I plan to
do a backwards-incompatible rewrite in order to address those issues.

[limitations]: https://gitlab.com/scottywz/elements#current-limitations


What Elements is
----------------

* **Elements is for distributing containerized applications in a form that
  is user-friendly.**  (Or at least, "command-line user-friendly".)  Users
  of Elements containers are not expected to know anything about container
  runtimes, registries, the `-i`, `-t`, or `--rm` options to Podman or
  Docker, how to use Docker securely, the internal filesystem layout of or
  port numbers used in the container, `/etc/subuid`/`/etc/subgid`, etc.  The
  only runtime dependency that is not normally included in most desktop
  distributions is runc.  (runc is not bundled for security reasons.)

* **Elements is for container authors who desire a simple container runtime
  with few surprises.**  This includes personal services, development
  tasks, and other cases where using (or learning) a more heavyweight runtime
  is not desirable.  Container registries are only a concern at build time,
  the container only exists while the AppImage is running, and the container
  image's location is always known.


What Elements is _not_
----------------------

* **Elements is not a replacement for Podman, rkt, Docker, or other mainstream
  container engines.**

* **Elements is not "enterprise-ready".**  It is designed for small-scale
  and mostly personal and development use cases.

* **Elements is not an orchestration engine.**  I do plan to add some support
  for pods, but this will be limited to shipping and running multiple
  container images in/from the same AppImage and sharing their resources.
  Also, like the containers themselves, major runtime options like resource
  sharing will be defined in the recipe file.

* **Elements does not interact with any container registries at runtime, and
  images are not OCI-compliant.**  This is due to the use cases for which
  Elements is designed.

* **Elements is not for low-level needs.**  Elements includes default
  behavior that is designed to remove some common pain points of running
  containers, such as allocating a TTY and mounting `/etc/resolv.conf`
  for DNS resolution.  Low-level options are hidden from both the container
  author and user.

* **Elements is not for critical applications.**  If your container failing
  would result in death; bodily injury; emotional distress; property damage
  or loss; financial loss; [blood, devastation, death, war, and horror][bddwh];
  incarceration; other legal action; and/or any other serious consequences;
  then Elements is not right for you.  If you choose to use it anyway for
  such containers, then you are doing so at your own risk.

[bddwh]: https://www.imdb.com/videoplayer/vi1619377433


{% include dev-warning.html %}
