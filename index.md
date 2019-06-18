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

{% include dev-warning.html %}


What Elements is
----------------

* **Elements is for distributing containerized applications in a form that
  is user-friendly.**  (Or at least, "command-line user-friendly".)  Users
  of Elements containers are not expected to know anything about container
  runtimes, registries, the `-i`, `-t`, `--rm`, or any other options to
  Podmabn or Docker, how to use Docker securely, the internal filesystem
  layout of or port numbers used in the container, etc.  Containers are
  expected to support rootless operation by default.  The only runtime
  dependency that is not normally included in most desktop distributions
  is runc (which is not bundled with images for security reasons.)

* **Elements is for container authors who desire a simple container runtime.**
  This includes personal services, development tasks, and other cases where
  using (or learning) a more heavyweight runtime is not desirable.  Container
  registries are only a concern at build time, the runc container only exists
  while the AppImage is running, and the user always knows where the container
  image is located.

* **Elements is for easy rootless containers.**  Elements containers are
  designed to run rootlessly without any extra configuration needed, even if
  this means making certain sacrifices.  For example, Elements containers
  should not rely on UID or GID mapping for any guest UID/GID other than 0
  (root), since users are not expected to configure `/etc/subuid` or
  `/etc/subgid`.


What Elements is _not_
----------------------

* **Elements is not a replacement for Podman, rkt, Docker, or other mainstream
  container engines.**  ELements is designed for small-scale containers and
  mostly personal, development, and end-user distribution use cases.

* **Elements is not "enterprise-ready".**  See above.

* **Elements is not an orchestration engine.**  I do plan to add some support
  for pods, but this will be limited to shipping and running multiple
  container images in/from the same AppImage and sharing their resources.
  Also, like the containers themselves, major runtime options like resource
  sharing will be defined in the definition file.

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
  then Elements is not right for your use case.  If you choose to use it
  anyway for such containers, then you are doing so at your own risk.

[bddwh]: https://www.imdb.com/videoplayer/vi1619377433
