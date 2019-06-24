#!/usr/bin/env python3
# vim: set fdm=marker sw=1:

__version__ = "___VERSION___"

# imports  {{{1
import argparse
import io
import os
import re
import shlex
import stat
import subprocess
import sys
import tarfile
import tempfile

from collections import OrderedDict
from typing import *


# constants  {{{1

TRUTHY = ("true", "1", "yes")
FALSY = ("false", "0", "no", "")
BOOLS = TRUTHY + FALSY


class ElementError(RuntimeError):  #{{{1
 message: Optional[str]
 spec: Optional[str]
 
 def __init__(self, message: Optional[str] = None, spec: Optional[str] = None) -> None:
  self.message = message
  self.spec = spec
 
 def __str__(self) -> str:
  result = ""
  if self.message:
   result += self.message
   if self.spec:
    result += "\n    "
  if self.spec:
   result += self.spec.rstrip("\r\n")
  return result


def main(argv):  #{{{1
 try:
  options = _parse_args(argv)
  if isinstance(options, int):
   return options
  
  if is_binary_file(options.def_):
   raise ElementError("`%s` is not a definition file" % options.def_)
  
  if os.path.exists(options.output) and not is_binary_file(options.output):
   raise ElementError("`%s` exists but is a text file" % options.output)
  
  with open(options.def_, "rb") as def_:
   el = Element(def_.read())
  
  el.build(options.output, os.path.dirname(options.def_),
           print_status=True, from_filename=options.def_)
 except RuntimeError as error:
  print("elements: error: " + str(error), file=sys.stderr)
  return 1


def _parse_args(argv):  #{{{1
 prog = os.path.basename(argv[0])
 prog = prog if prog != "__main__.py" else "elements"
 
 p = argparse.ArgumentParser(
  prog=prog,
 )
 p.add_argument("--hep", dest="_hep_easter_egg", action="store_true",
                help=argparse.SUPPRESS)
 p.add_argument("-V", "--version", action="store_true",
                help="show version number and exit")
 p.add_argument("def_", metavar="def_file", default=None, nargs="?",
                help="the Singularity definition file with Elements extensions"
                     " from which to build")
 p.add_argument("output", metavar="output_file", default=None, nargs="?",
                help="the output filename")
 
 required = {
  "def_": "def_file",
  "output": "output_file"
 }
 
 def _fix_usage(s):
  s = s.split("\n\n", 1)
  for k in required:
   v = required[k]
   s[0] = s[0].replace("[%s]" % v, v)
  return "\n\n".join(s)
 _format_usage = p.format_usage
 _format_help = p.format_help
 p.format_usage = lambda: _fix_usage(_format_usage())
 p.format_help = lambda: _fix_usage(_format_help())
 
 try:
  options = p.parse_args(argv[1:])
  if not options.version and not options._hep_easter_egg:
   missing = [required[k] for k in required if getattr(options, k, None) is None]
   verb = " is" if len(missing) == 1 else "s are"
   if len(missing):
    p.error("the following argument%s required: %s" % (verb, ", ".join(missing)))
 except SystemExit as exc:
  return exc.code
 
 if options._hep_easter_egg:
  print("Hep!  Hep!  I'm covered in sawlder! ... Eh?  Nobody comes.")
  print("--Red Green, https://www.youtube.com/watch?v=qVeQWtVzkAQ#t=6m27s")
  return 0
 
 if options.version:
  print(__version__)
  return 0
 
 return options


class Element:  #{{{1
 def_: bytes
 
 args: List["Arg"]
 binds: List["Bind"]
 env: List["Env"]
 
 config: Dict[str, Union[str, int, bool]]
 
 CONFIG_DEFAULTS = {
  "args": "",
  "bind": "",
  "env": "",
  "name": "elements",
  "ps1-color": 27,
  "resolv": True,
  "root-copyup": False,
  "terminal": True,
  "_do_output": False
 }
 
 SPECIAL_ENV = [
  # here, a leading ^ means before user variables and a leading $ means after
  
  # Constants
  #"$ELEMENTS_MAGIC=Elements",  # defined in loader
  "$ELEMENTS_VERSION=" + __version__,
  
  # Container config values
  "$ELEMENTS_NAME=$__CONFIG_NAME",
  "$ELEMENTS_PS1_COLOR=$__CONFIG_PS1_COLOR",
  
  # Runtime values
  # "^ELEMENTS_INSTANCE=%",  # defined in loader and overwritten by `instance` type args
  "$ELEMENTS_ARGV0=$ARGV0",
  #"$ELEMENTS_ID=$ELEMENTS_NAME.$ELEMENTS_INSTANCE"  # defined in loader
 ]
 
 def __init__(self, def_) -> None:  #{{{2
  self.def_ = def_
  self.args = list()
  self.binds = list()
  self.env = list()
  
  self.config = {}
  for key in self.CONFIG_DEFAULTS:
   default = self.CONFIG_DEFAULTS[key]
   if isinstance(default, bool):
    self.config[key] = bool(default)
   else:
    self.config[key] = str(default)
 
 def build(self, to_filename: str, context_dir: str,  #{{{2
           print_status: bool = False, from_filename: str = "") -> None:
  def _chmod_x(path):
   os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
  
  def _status(msg: str = "", color: int = 7, intensity: int = 1):
   if print_status:
    print("\033[0;%d;3%dm%s\033[0m" % (intensity, color, msg), file=sys.stderr)
  
  _status("Elements v%s" % __version__)
  _status()
  
  self._parse()
  
  with tempfile.TemporaryDirectory(prefix=".elements-build.") as tmp:
   # build bootstrap fs archive  #{{{3
   _status("Building bootstrap filesystem...")
   with tempfile.TemporaryDirectory(prefix="bootstrap.", dir=tmp) as bootstrap_dir:
    bootstrap_def = os.path.join(bootstrap_dir, "bootstrap.def")
    with open(bootstrap_def, "wb") as f:
     f.write(BOOTSTRAP_DEF)
    
    bootstrap_root = os.path.join(bootstrap_dir, "rootfs")
    self._run(["singularity", "build", "--sandbox", bootstrap_root, bootstrap_def],cwd=tmp)
    
    bootstrap_tar = os.path.join(tmp, "bootstrap.tar")
    with tarfile.open(bootstrap_tar, "w") as tar:
     tar.add(bootstrap_dir, arcname=".", recursive=True)
   _status("")
   
   # rootfs status message  #{{{3
   _status("Building root filesystem%s..."
           % (" from `%s`" % from_filename if from_filename else ""))
   
   # build rootfs  #{{{3
   element_def = os.path.join(tmp, "element.def")
   with open(element_def, "wb") as f:
    f.write(self.def_)
   
   element_root = os.path.join(tmp, "rootfs")
   self._run(["singularity", "build", "--sandbox", element_root, element_def],
             cwd=context_dir)
   
   entry = os.path.join(element_root, ".elements-entry")
   with open(entry, "wb") as f:
    f.write(ELEMENTS_ENTRY)
   _chmod_x(entry)
   
   # /exec, /sh, and /out  #{{{3
   exec_ = os.path.join(element_root, "exec")
   with open(exec_, "wb") as f:
    f.write(b"#!/bin/sh\n\nexec /.singularity.d/actions/exec \"$@\"\n")
   _chmod_x(exec_)
   
   sh = os.path.join(element_root, "sh")
   with open(sh, "wb") as f:
    f.write(SH_SCRIPT)
   _chmod_x(sh)
   
   out = os.path.join(element_root, "out")
   if self.config["_do_output"]:
    os.mkdir(out)
   
   # PS1 scripts  {{{3
   env_base = os.path.join(element_root, ".singularity.d", "env", "99-base.sh")
   with open(env_base, "rb") as f:
    env_base_code = f.read()
   with open(env_base, "wb") as f:
    f.write(re.sub(br"\n(PS1=[^\n]*)", b"\n#\\1\nPS1=$PS1", env_base_code))
   
   color = os.path.join(element_root, ".color")
   with open(color, "wb") as f:
    f.write(PS1_SCRIPT)
   _chmod_x(color)
   
   ps1_env = os.path.join(element_root, ".singularity.d", "env", "02-elements-ps1.sh")
   with open(ps1_env, "wb") as f:
    f.write(PS1_ENV_SCRIPT)
   _chmod_x(ps1_env)
   
   # AppImage status message  #{{{3
   _status()
   _status("Building AppImage `%s`..." % to_filename)
   
   # AppImage dummy files  #{{{3
   desktop = os.path.join(tmp, "dummy.desktop")
   with open(desktop, "wb") as f:
    f.write(APPIMAGE_DESKTOP)
   
   icon = os.path.join(tmp, "dummy.png")
   with open(icon, "wb") as f:
    pass
   
   diricon = os.path.join(tmp, ".DirIcon")
   os.symlink(os.path.basename(icon), diricon)
   
   # compile loader and AppRun  #{{{3
   loader = os.path.join(tmp, "elements-loader.sh")
   with open(loader, "wb") as f:
    f.write(self._compile_loader())
  
   apprun = os.path.join(tmp, "AppRun")
   with open(apprun, "wb") as f:
    f.write(APPRUN.replace(b"___loader___", os.path.basename(loader).encode("utf8")))
   _chmod_x(apprun)
   
   # output, cleanup, license, and version  #{{{3
   output = os.path.join(tmp, "elements-output.sh")
   with open(output, "wb") as f:
    f.write(OUTPUT)
   _chmod_x(output)
   
   cleanup = os.path.join(tmp, "elements-cleanup.sh")
   with open(cleanup, "wb") as f:
    f.write(CLEANUP)
   _chmod_x(cleanup)
   
   license = os.path.join(tmp, "LICENSE.Elements.txt")
   with open(license, "wb") as f:
    f.write(LICENSE)
   
   version = os.path.join(tmp, "VERSION.Elements.txt")
   with open(version, "wb") as f:
    f.write(__version__.encode("utf-8"))

   # build AppImage  #{{{3
   arch = cast(Any, os.uname()).machine.lower().replace("_", "").replace("-", "")
   if "x8664" in arch or "amd64" in arch:
    arch = "x86_64"
   elif "aarch64" in arch or "arm64" in arch:
    arch = "aarch64"
   else:
    arch = None
   
   appimagetool_env = os.environ.copy()
   if arch:
    appimagetool_env["ARCH"] = arch
   
   self._run(["appimagetool", "--no-appstream", tmp, to_filename], env=appimagetool_env)
   _chmod_x(to_filename)
   
   # finished status message  #{{{3
   _status()
   _status("Built `%s`%s."
           % (to_filename, 
              " from `%s`" % from_filename if from_filename else ""))
 
 def _run(self, cmd: List[Union[str, bytes]], *args, **kwargs):  #{{{2
  name_any = cmd[0]
  if isinstance(name_any, bytes):
   name = name_any.decode(sys.getfilesystemencoding())
  else:
   name = str(name_any)
  
  check = True
  if "check" in kwargs and not kwargs["check"]:
   check = False
  kwargs["check"] = False
  
  try:
   r = subprocess.run(cmd, *args, **kwargs)
  except FileNotFoundError:
   raise ElementError("%s is not installed on the PATH" % name)
  if check and r.returncode:
   raise ElementError("%s failed with exit code %d" % (name, r.returncode))
  
  return r
   
 def _parse(self) -> None:  #{{{2
  self._parse_def()
  self._parse_args(str(self.config["args"]))
  self._parse_binds(str(self.config["bind"]))
  self._parse_env(str(self.config["env"]))

 def _parse_def(self) -> None:  #{{{2
  LINE_MAGIC = b"#Elements."
  LINE_MAGIC_LEN = len(LINE_MAGIC.decode("utf-8"))
  
  reader = io.BytesIO(self.def_)
  line = ""
  continuation = False
  for line_bytes in reader:
   line_bytes = line_bytes.strip()
   if line_bytes.startswith(b"%"):
    break
   
   if line_bytes.startswith(LINE_MAGIC):
    line = line_bytes.decode("utf-8")
    continuation = line.endswith("\\")
   elif continuation:
    if line_bytes.startswith(b"#"):
     if line_bytes[1:].lstrip().startswith(b"#"):
      continue
     line += " " + line_bytes[1:].lstrip().decode("utf-8")
     continuation = line.endswith("\\")
    else:
     continuation = False
   
   if line:
    if continuation:
     line = line[:-1].rstrip()
    else:
     value: Union[str, int, bool]
     
     item = line[LINE_MAGIC_LEN:]
     key, value = [i.rstrip() for i in item.split(":", 1)]
     value = value.lstrip()
     
     if key.lstrip() != key:
      raise ElementError("whitespace is not allowed before config key names:", line)
     if key not in self.CONFIG_DEFAULTS.keys():
      raise ElementError("invalid config key \`%s\`:" % key, line)
     
     if isinstance(self.config[key], bool):
      value = parse_bool(value, line, "%s has an" % key)
     
     if isinstance(self.config[key], int):
      try:
       value = int(value)
      except ValueError:
       raise ElementError("%s must be an integer:" % key, line)
     
     self.config[key] = value
     continuation = False
     line = ""

 
 def _parse_args(self, spec: str) -> None:  #{{{2
  args = shlex.split(spec)
  for arg in args:
   value = Arg(self, arg)
   self.args += [value]
 
 def _parse_env(self, spec: str) -> None:  #{{{2
  envs = shlex.split(spec)
  self.env += [Env(self, i[1:]) for i in self.SPECIAL_ENV if i.startswith("^")]
  self.env += [Env(self, i) for i in envs]
  self.env += [Env(self, i[1:]) for i in self.SPECIAL_ENV if i.startswith("$")]


 def _parse_binds(self, spec: str) -> None:  #{{{2
  binds = shlex.split(spec)
  self.binds += [Bind(self, i) for i in binds]
 
 def _compile_loader(self) -> bytes:  #{{{2
  result = LOADER_TPL
  
  result = result.replace(b"___config_args___", self._compile_args().encode("utf-8"))
  result = result.replace(b"___config_env___", self._compile_env().encode("utf-8"))
  result = result.replace(b"___config_binds___", self._compile_binds().encode("utf-8"))
  result = result.replace(b"___config_misc___", self._compile_misc().encode("utf-8"))
  
  return result
 
 def _compile_misc(self) -> str:   #{{{2
  result = "config_misc() {\n%s\n}"
  blocks: List[str] = []
  
  blocks += [
   "__CONFIG_NAME=" + str(self.config["name"] or self.CONFIG_DEFAULTS["name"]),
   "__CONFIG_PS1_COLOR=%d" % int(self.config["ps1-color"]),
   "__CONFIG_RESOLV=%d" % int(self.config["resolv"]),
   "__CONFIG_ROOT_COPYUP=%d" % int(self.config["root-copyup"]),
   "__CONFIG_TERMINAL=" + str(self.config["terminal"]).lower(),
   "__CONFIG__DO_OUTPUT=%d" % int(self.config["_do_output"])
  ]
  
  result %= "\n".join([" " + i for i in blocks])
  return result
 
 def _compile_args(self) -> str:   #{{{2
  optstring = ""
  for arg in self.args:
   if arg.is_flag:
    optstring += arg.sh_var
    if not arg.is_bool:
     optstring += ":"
  
  result = """
config_args() {
 __config_init_bool_flags
 __parse_args '%s' "$@"
}
""".strip() % optstring
  arg_fns: List[str] = []

  init_bool_flags_fn = "__config_init_bool_flags() {\n%s\n}\n\n"
  init_bool_flags_items: List[str] = []
  
  pos_i = 1
  for arg in self.args:
   type_ = "pos" if arg.is_positional else "flag"
   fn_arg_name = str(pos_i) if arg.is_positional else arg.sh_var
   fn_code = "__config_%s_arg_%s() {\n%s\n}"
   fn_code %= (type_, fn_arg_name, arg.compile().strip("\n"))
   arg_fns += [fn_code]
   if arg.is_bool:
    init_bool_flags_items += [" %s=0" % arg.sh_var]
   if arg.is_positional:
    pos_i += 1
  
  if not len(init_bool_flags_items):
   init_bool_flags_items += [" true"]
  
  result += "\n\n"
  result += init_bool_flags_fn % "\n".join(init_bool_flags_items)
  result += "\n\n".join(arg_fns)
  return result
  
 def _compile_env(self) -> str:   #{{{2
  result = "config_env() {\n%s\n}"
  env_fns: Dict[str, str] = OrderedDict()
  
  env_i = 1
  for env in self.env:
   fn_name = "__config_env_%d" % env_i
   fn_code = "%s() {\n%s\n}" % (fn_name, env.compile().strip("\n"))
   env_fns[fn_name] = fn_code
   env_i += 1
  
  if len(env_fns):
   result %= "\n".join([" " + i for i in env_fns.keys()])
   for fn in env_fns.values():
    result += "\n\n" + fn
  else:
   result %= " true"
  
  return result
  
 def _compile_binds(self) -> str:   #{{{2
  result = "config_binds() {\n%s\n}"
  bind_fns: Dict[str, str] = OrderedDict()
  
  bind_i = 1
  for bind in self.binds:
   fn_name = "__config_bind_%d" % bind_i
   fn_code = "%s() {\n%s\n}" % (fn_name, bind.compile().strip("\n"))
   bind_fns[fn_name] = fn_code
   bind_i += 1
  
  if len(bind_fns):
   result %= "\n".join([" " + i for i in bind_fns.keys()])
   for fn in bind_fns.values():
    result += "\n\n" + fn
  else:
   result %= " true"
  
  return result
  
class Item:  #{{{1
 el: Element
 spec: str
 
 def __init__(self) -> None:
  raise NotImplementedError
 
 def compile(self) -> str:
  raise NotImplementedError
 
 def _esc_var_str(self, s: str) -> str:
  NUM_RE = r"([0-9]|\{[0-9]+\})"
  ANUM_RE = r"([a-zA-Z_][a-zA-Z_0-9]*)"
  VAR_NAME_RE = r"(%s|%s|\{%s\})" % (NUM_RE, ANUM_RE, ANUM_RE)
  m = re.match(r"^(?P<var>((\$%s)?))(?P<rest>.*)$" % VAR_NAME_RE,
               s, re.DOTALL)
  var = m.group("var") if m else ""
  if var:
   var = '"%s"' % var
  rest = m.group("rest") if m else ""
  if rest:
   rest = "'%s'" % rest.replace("'", "'\\''")
  return var + rest


class Arg(Item):  #{{{1
 #Elements.args: 1:bind>/srv:ro 2:env>PORT:int -H:env>HOST -v:env>VERBOSE:bool \
 #               -d:bind>/data -n:instance
 key: str
 sh_var: str
 kind: str
 value: Any
 
 is_flag: bool = False
 is_positional: bool = False
 
 is_bool: bool = False
 
 KINDS = ["env", "bind", "instance", "output"]
 
 def __init__(self, el: Element, spec: str) -> None:  #{{{2
  self.el = el
  self.spec = spec
  if ">" in spec:
   lhs, rhs = spec.split(">", 1)
  else:
   lhs, rhs = spec, ""
  self.key, self.kind = lhs.split(":", 1)
  
  if self.key.startswith("-"):
   self.is_flag = True
   if not re.match(r"^-[a-zA-Z0-9]{1}$", self.key):
    raise ElementError("flag argument name must be a single alphanumeric character:", spec)
   elif not self.key.startswith("-"):
    raise ElementError("flag argument spec must start with a hyphen:", spec)
  else:
   self.is_positional = True
   if not re.match(r"^[a-zA-Z_][a-zA-Z_0-9]+$", self.key):
    raise ElementError("positional argument metavar must be a valid POSIX shell"
                       " variable name and longer than 1 character:", spec)
  
  if self.is_positional:
   self.sh_var = self.key
  else:
   self.sh_var = self.key.lstrip("-")
  
  self.kind = self.kind.strip().lower()
  if self.kind not in self.KINDS:
   raise ElementError("argument kind must be one of %s:" % ",".join(self.KINDS), spec)
  
  env_export = True
  
  if self.kind == "instance":
   rhs = "ELEMENTS_%s=%s" % (self.kind.upper(), rhs)
   self.kind = "env"
   env_export = False
  if self.kind == "output":
   rhs = "__CONFIG_%s=%s" % (self.kind.upper(), rhs)
   self.kind = "env"
   env_export = False
   self.el.config["_do_output"] = True
  
  if self.kind == "bind":
   self.value = Bind(self.el, spec=rhs, _from=lhs + ">", _src="${%s}" % self.sh_var)
  elif self.kind == "env":
   self.value = Env(self.el, spec=rhs, _from=lhs + ">", _value="${%s}" % self.sh_var,
                    _export=env_export)
   if self.value.type_ == "bool":
    self.is_bool = True
    self.value._from = ""
    self.value.type_ = "str"
    self.el.env += [self.value]
 
 def compile(self) -> str:  #{{{2
  TPL = r"""
 local __compile_what=%s
 %s=%s
 """
  
  sh_value = "1" if self.is_bool else "$__COMPILE_ARG_VALUE"
  result = TPL % (self.key, self.sh_var, sh_value)
  
  if self.kind != "env" or not self.is_bool:
   result += self.value.compile()
  
  return result


class Env(Item):  #{{{1
 #Elements.env: TEST=hello API_KEY:int=$HOST_VAR HOST_CONF_FILE=$HOST/.config.yml
 name: str
 type_: str
 value: str
 
 _from: str = ""
 _export: bool = True
 
 TYPES = ["str", "int", "bool"]
 
 def __init__(self, el: Element, spec: str,  #{{{2
              _from: str = "", _value: str = None, _export: bool = True) -> None:
  self.el = el
  self.spec = spec
  self._from = _from
  self._export = _export
  
  lhs, self.value = (spec if "=" in spec else spec + "=").split("=", 1)
  if ":" in lhs:
   self.name, self.type_ = [i.strip() for i in lhs.split(":", 1)]
  else:
   self.name = lhs.strip()
   self.type_ = "str"
  
  if not re.match(r"^[a-zA-Z_][a-zA-Z_0-9]+$", self.name):
   raise ElementError("environment variable name must be a valid POSIX shell"
                      " variable name and longer than 1 character:", spec)
  
  if _value is not None:
   self.value = _value
  
  self.type_ = self.type_.strip().lower()
  if self.type_ not in self.TYPES:
   raise ElementError("env var type must be one of %s:" % ", ".join(self.TYPES),
                      _from + spec)
 
 def compile(self) -> str:  #{{{2
  TPL = r"""
%s local __compile_env_name __compile_env_value
 __compile_env_name=%s
 __compile_env_value=%s
 %s
 eval "$__compile_env_name=\"\$__compile_env_value\""
%s
"""
  
  if not self._from:
   compile_what = " local __compile_what=%s\n" % self._esc_var_str(self.name)
  else:
   compile_what = ""
  
  if self.type_ == "int":
   typecheck = r"""
 if ! ( (printf '%s' "$__compile_env_value" | tr '\n' ' '; echo) | grep -q '^-\?[0-9]\+$')
 then
  echo "$ARGV0: error: $__compile_what must be an integer" >&2
  exit 2
 fi
 """
  elif self.type_ == "bool":
   truthy = " || ".join(['[ x"$__compile_env_value" = x"%s" ]' % i for i in TRUTHY])
   falsy = " || ".join(['[ x"$__compile_env_value" = x"%s" ]' % i for i in FALSY])
   bools = ", ".join(['"%s"' % i for i in BOOLS])
   typecheck = r"""
 if %s; then
  __compile_env_value=1
 elif %s; then
  __compile_env_value=0
 else
  echo "$ARGV0: error: $__compile_what has an invalid boolean value (must be one of %s)">&2
  exit 2
 fi
 """ % (truthy, falsy, bools)
  else:
   typecheck = ""
  
  value = self.value
  
  if self._export:
   export = """
 _jq --arg item "$__compile_env_name=$__compile_env_value" '.process.env |= . + [$item]'
""".lstrip("\n")
  else:
   export = ""
  
  params = [compile_what]
  params += [self._esc_var_str(i) for i in (self.name, value)]
  params += [typecheck, export]
  return TPL % tuple(params)


class Bind(Item):  #{{{1
 #Elements.bind: $docroot/lighttpd.conf:/srv/lighttpd.conf:ro \
 #               $d/precious.txt:/data/precious.txt:ro
 src: str
 dest: str
 flags: List[str]
 
 _from: str = ""
 
 FLAGS = ["rw", "ro"]
 
 def __init__(self, el: Element, spec: str,  #{{{2
              _from: str = "", _src: str = None) -> None:
  self.el = el
  self.spec = spec
  self._from = _from
  
  parts = spec.split(":")
  n_parts = "2 or 3"
  
  if _src is not None:
   parts = [_src] + parts
   n_parts = "1 or 2"
  
  if not 2 <= len(parts) <= 3:
   raise ElementError("bind must have either %s parameters:" % n_parts, _from + spec)
  
  if len(parts) == 2:
   parts += [""]
  
  self.src, self.dest, flags = parts
  
  self.flags = flags.split(",") if flags.strip() else []
  for i in self.flags:
   if i.strip().lower() not in self.FLAGS:
    raise ElementError("bind flags must be one of %s:" % ", ".join(self.FLAGS),
                       _from + spec)
 
 def compile(self) -> str:  #{{{2
  TPL = r"""
 local __compile_bind_src __compile_bind_dest
 __compile_bind_src=$(abspath %s)
 
 if ! [ -e "$__compile_bind_src" ]; then
  echo "$ARGV0: error: \`$__compile_bind_src\`: no such file or directory" >&2
  exit 1
 elif ! [ -r "$__compile_bind_src" ]; then
  echo "$ARGV0: error: \`$__compile_bind_src\` is not readable" >&2
  exit 1
 fi
 
 _jq --arg src "$__compile_bind_src" --arg dest %s --arg mode %s \
  '.mounts |= . + [{
   "destination": $dest,
   "type": "bind",
   "source": $src,
   "options": [
     "rbind",
     $mode
   ]
  }]'
"""
  
  mode = "rw"
  for i in self.flags:
   if i in ("rw", "ro"):
    mode = i
  
  return TPL % tuple([self._esc_var_str(i) for i in (self.src, self.dest, mode)])


def is_binary_file(path: str) -> bool:  #{{{1
 with open(path, "rb") as f:
  test = f.read(512)
 
 try:
  test.decode("utf-8")
 except UnicodeDecodeError:
  return True
 
 for i in test:
  if i < 32 and i not in b'\t\n\r\x0b\x0c\x1b':
   return True
 
 return False


def parse_bool(value: Union[str, int, bool],  #{{{1
               line: Optional[str] = None, msg_prefix: Optional[str] = None) -> bool:
 if isinstance(value, (int, bool)):
  return bool(value)
 if value in TRUTHY:
  return True
 elif value in FALSY:
  return False
 else:
  msg_prefix_str = str(msg_prefix) + " " if msg_prefix else ""
  colon = ":" if line else ""
  bool_list = ", ".join('"%s"' % i for i in BOOLS)
  raise ElementError("%sinvalid boolean value (must be one of %s)%s"
                     % (msg_prefix_str, bool_list, colon), line)


# LOADER_TPL  #{{{1
LOADER_TPL: bytes = br"""___LOADER_TPL___"""


# APPRUN  #{{{1
APPRUN: bytes = br"""
#!/bin/sh

if [ x"$APPDIR" = x"" ]; then
 echo "AppRun: error: could not find mount point" >&2
 exit 127
fi


start() {
 if [ x"$__ELEMENTS_USE_DASH" = x"1" ]; then
  exec dash "$APPDIR/___loader___" "$@"
 else
  exec sh "$APPDIR/___loader___" "$@"
 fi
}


if [ x"$__ELEMENTS_CTR_DEBUG" = x"1" ]; then
 printf '\n%s ' "debug time ;)" >&2; read
 start "$@"
 printf '\n%s ' "debug time ;)" >&2; read
else
 start "$@"
fi
""".lstrip()


# APPIMAGE_DESKTOP  #{{{1
APPIMAGE_DESKTOP: bytes = br"""
[Desktop Entry]
Type=Application
Name=An Elements Container
Categories=
Exec=false
Icon=dummy
Terminal=true
""".lstrip()


# BOOTSTRAP_DEF  #{{{1
BOOTSTRAP_DEF: bytes = br"""
Bootstrap: docker
From: alpine

%post
 apk add jq
 rm -f /var/cache/apk/APKINDEX.*
""".lstrip()


# CLEANUP  #{{{1
CLEANUP: bytes = br"""
#!/bin/sh

if [ x"$1" = x"" ]; then
 echo "$0: error: bundle directory not given" >&2
 exit 2
fi

bundle=$1
shm=$2
out_tmp=$3

if (! [ -f "$bundle/magic" ]) || [ x"$(cat "$bundle/magic")" != x"Elements" ]; then
 echo "$0: error: bundle is not an Elements bundle" >&2
 exit 2
fi

rm -f "$bundle/appdir"
rm -rf "$bundle"

if [ x"$shm" != x"" ] && [ -d "$shm" ]; then
 chmod -R +w "$shm"
 rm -rf "$shm"
fi

if [ x"$out_tmp" != x"" ] && [ -d "$out_tmp" ]; then
 chmod -R +w "$out_tmp"
 rm -rf "$out_tmp"
fi
""".lstrip()


# OUTPUT  #{{{1
OUTPUT: bytes = br"""
#!/bin/sh

if [ $# -ne 6 ]; then
 echo "$0: usage: $0 argv0 id out-tmp-dir inside-src pwd outside-dest" >&2
 exit 2
fi

argv0=$1
id=$2
out_tmp=$3
src=$4
pwd=$5
dest=$6

if [ x"$dest" = x"" ]; then
 exit
fi

if ! [ -d "$pwd" ]; then
 echo "$argv0: error: working directory \`$pwd\` is no longer a directory" >&2
 exit
fi

cd "$pwd"

if [ -d "$dest" ]; then
 dest="$dest/$id.out"
fi

#if [ -e "$dest" ]; then
# read -p "$argv0: Overwrite \`$dest\` (y/N)? " -r answer
# if ! (printf '%s\n' "$answer" | grep -q -e '^[yY]'); then
#  exit
# fi
#fi

src="$out_tmp/$src"

entries=$(ls -A -1 "$src" | wc -l)
if [ x"$entries" = x"0" ]; then
 exit
elif [ x"$entries" = x"1" ]; then
 src="$src/$(ls -A -1 "$src" | head -n 1)"
fi

mv "$src" "$dest" || true
""".lstrip()


# LICENSE  #{{{1
LICENSE: bytes = br"""___LICENSE___"""


# PS1_SCRIPT  #{{{1
PS1_SCRIPT: bytes = br"""
#!/bin/sh

PS1=$(__ps1_color() {
 local color default plain C I
 
 color=$1
 default=17
 plain=$(printf '%s' "$PS1" | sed -e 's/\033\[[^m]*m//g')
 
 if [ x"$TERM" != x"" ]; then
  C=${color:-${ELEMENTS_PS1_COLOR:-$default}}  # n/10 = intensity; n%10 = color
  if (printf '%s\n' "$C" | grep -q -e '[^0-9]'); then
   C=${ELEMENTS_PS1_COLOR:-$default}
  fi
  if [ x"$C" != x"0" ]; then
   I=$((C / 10)); I=${I%.*$}; C=$((C % 10))
   printf '\033[%s' "${I};3${C}m$plain" '0m'
   return
  fi
 fi
 
 printf '%s' "$plain"
}; __ps1_color "$1")
""".lstrip()


# PS1_ENV_SCRIPT  #{{{1
PS1_ENV_SCRIPT: bytes = br"""
#!/bin/sh

PS1='$HOSTNAME${HOSTNAME:+:}$ELEMENTS_ID:$(pwd=$(pwd); [ x"$pwd" = x"$HOME" ] && printf '%s~' '' || (printf '%s' "$pwd" | sed -e "s,/$,,"; echo /)) '

. /.color "$ELEMENTS_PS1_COLOR"
""".lstrip()


# SH_SCRIPT  #{{{1
SH_SCRIPT: bytes = br"""
#!/bin/sh

if [ -x "/bin/bash" ]; then
 exec /exec /bin/bash --norc "$@"
elif [ -x "/bin/ash" ]; then
 exec /exec /bin/ash "$@"
else
 exec /exec /bin/sh "$@"
fi
""".lstrip()


# ELEMENTS_ENTRY  #{{{1
ELEMENTS_ENTRY: bytes = br"""
#!/bin/sh

exec /.singularity.d/actions/run "$@"
""".lstrip()


if __name__ == "__main__":  #{{{1
 try:
  sys.exit(main(sys.argv))
 except KeyboardInterrupt:
  pass
