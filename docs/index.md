---
title: Documentation
---

{% include dev-warning.html %}
{% include contents-float.html %}

Contents
--------

* [Usage](#usage)
* [Elements extensions](#elements-extensions)
    * [args](#args)
        * [Argument types](#argument-types)
            * [bind](#bind)
            * [env](#env)
            * [instance](#instance)
    * [bind](#bind-1)
    * [env](#env-1)
    * [Miscellaneous options](#miscellaneous-options)
        * [name](#name)
        * [resolv](#resolv)
        * [terminal](#terminal)
        * [ps1-color](#ps1-color)


Usage
-----

Create a [Singularity Definition File][sdf] for your container.  You may
use [Elements extensions as described below](#elements-extensions).  The
recommended file extension for definition files is `.def`.

Most Singularity sections are supported, with these exceptions:

  * `%help` (planned)
  * `%startscript` (your host's init system is recommended instead)
  * `%test`
  * All app-related sections (anything that starts with `%app`)

(Those sections will not cause the build to fail, but the features they
represent are not available at runtime.)

After creating a definition file, run the following command as root:

    # elements {definition-file} {output-file}

The output file will be an executable AppImage containing everything needed
to run the container with the exception of runc.  Since it will likely
be used on the command line, no file extension is recommended.  If an
extension is necessary, `.Element` is recommended.


[sdf]: https://www.sylabs.io/guides/3.0/user-guide/definition_files.html


Elements extensions
-------------------

Elements extends the Singularity Definition File format using specially
formatted comments.  These extensions let you control if and how parameters
such as bind mounts and environment variables are passed as arguments
to the container's AppImage.  All extensions are optional.

An extension takes the form of a comment starting with `#Elements.{name}:`,
where `{name}` is the name of the extension.  Whitespace is allowed before,
but not after, the number sign.  Elements extensions may appear before,
in between, or after the Singularity headers, but all extensions MUST
appear before any Singularity sections (which start with a % sign).

Extensions may be broken into separate lines by ending the first line with
a backslash and starting the next line with optional whitespace and a number
sign.

### args

    #Elements.args: {name}:{type}[{separator}{parameters} [...]

Example:

    #Elements.args: docroot:bind>/srv -a:bind>/app:ro \
    #               -H:env>HOST -p:env>PORT:int -i:instance

`args` allows you to control if and how parameters are passed as
arguments to the container's AppImage.  Short-form flags and positional
arguments are supported.  [Argument types are documented
below.](#argument-types)

For positional arguments, the name must be two or more characters long
and be a valid shell variable name.  For flag arguments, the name is a
hyphen followed by the flag character.  The separator is currently a
greater-than sign (`>`) for all argument types which take parameters.

User-supplied values are available to subsequent argument definitions
and to other Elements extensions using basic shell variable syntax,
i.e. `$var` or `${var}`.  The variable name will be the name of a
positional argument or the flag character of a flag argument.  Only
one variable can be used at the start of a parameter.


#### Argument types


##### bind

    {name}:bind>{dest}[:{flags}]

Binds a path on the host (the user-supplied value) to the `dest` path
inside the container.  Flags are comma-separated.  Currently, the only
two flags are `ro` (read-only) and `rw` (read-write, the default).


##### env

    {name}:env>{dest}[:{type}]

Defines the `dest` environment variable inside the container.  Valid
types are `str` (the default), `int`, and `bool` (valid values are
`true`, `1`, `yes`, `false`, `0`, `no`, or ``; case-insensitive).  If
the user supplies an invalid value for an integer or boolean variable,
execution will fail before the container is started.


##### instance

    {name}:instance

Defines the container's unique instance ID which is joined with [the
container's name](#name) by a dot to form the runc container ID.  If
the instance ID contains a `%` character, then that character will be
replaced with 12 random alphanumeric characters.  If the user omits
this argument, or if you don't define it, then the instance ID
defaults to `%` (i.e. 12 random alphanumeric characters).

Valid characters are 0-9, A-Z, a-z, `_`, `-`, `+`, `.`, and `%`.
Except for `%`, this is enforced by runc.

The runc container ID will be of the format \`[{name}](#name).{instance}\`.


### bind

    #Elements.bind: {src}:{dest}[:{flags}]

Example:

    #Elements.bind: $docroot/.nginx.conf:/srv/.nginx.conf:ro \
    #               $a/uploads:/srv/uploads:rw

`bind` allows you to bind arbitrary paths on the host to a destination
inside the container.  This is mainly intended for remounting specific
files or subdirectories from a user-provided bind mount with different
write-access flags, or making files from one user-provided bind mount
available in another, as shown in the above example.  You should not
bind paths that were not explicitly given to you by a user.

As described in [the `args` section](#args), the names of arguments are
available as variables for use in the `src` side of a bind mount here.
The variable must be at the start of the path, and only one variable
can be used per source path.  (Technically, variables can also be used
on the destination side with the same restrictions, but this is not
likely to be useful.)

Environment variables defined as arguments or in [the `env`
extension](#env-1) are also available as variables to bind mounts that
are directly defined here.  These variables are subject to the usual
restrictions.

The flags are the same as for [`bind` argument definitions](#bind).


### env

    #Elements.env: {name}[:{type}]={value} [...]

Example:

    #Elements.env: API_KEY=$HOST_VAR NUCLEAR_CODES:int=$ALL_ZEROES \
    #              DOCROOT=$docroot DEBUG:bool=$APP_DEBUG CONSTANT=42

`env` allows you to pass environment variables from the host or argument
definitions, or constant values, to the container.  As with [`env` argument
definitions](#env), integer and boolean values are validated before starting
the container, and the list of supported types is the same.

As described in [the `args` section](#args), the names of arguments are
available as variables for use in the `value` side of an environment
variable here.  The variable must be at the start of the value, and only
one variable can be used per value.

Environment variables defined here are also available as variables to
bind mounts that are defined directly in [the `bind` extension](#bind-1)
(but not those defined as arguments).  These variables are subject to the
usual restrictions.


### Miscellaneous options

    #Elements.{name}: {value}

A few other options can be set using Elements extensions.  Integer and
boolean values are validated at compile time using the same rules as
for integer and boolean argument values at run time.


#### name

(str) A non-unique name for the container which is joined with [the
instance ID](#instance) by a dot to create the runc container ID.
Defaults to `elements`.

Valid characters are 0-9, A-Z, a-z, `_`, `-`, `+`, and `.`.  This is
enforced by runc.

The runc container ID will be of the format \`{name}.[{instance}](#instance)\`.


#### resolv

(bool) Whether to automatically bind mount `/etc/resolv.conf` in the
container.  Defaults to true.


#### terminal

(bool) Whether to attach a terminal to the process.  Defaults to true.

If standard input is not a terminal, then no terminal will be attached
regardless of this setting.


#### ps1-color

(int) The color to use for the PS1 prompt in interactive shell sessions.
Defaults to 27 (dim white).  The value is a one- or two-digit number in
one of the following groups.  The last digit is an ANSI 4-bit color code
(0=black, 1=red, 2=green, 3=yellow, 4=blue, 5=magenta, 6=cyan, 7=white).

  * 0 (special case) - do not color the prompt
  * 1–7 - normal intensity
  * 10–17 - high intensity
  * 20–27 - dim intensity

The color can also be changed at runtime by sourcing `/.color` with the
desired color as an argument.
