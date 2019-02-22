#!/bin/sh
# vim: set fdm=marker fdl=1 sw=1:

# version: ___VERSION___

# script setup  #{{{2

set -e

if [ x"$__ELEMENTS_CTR_DEBUG" = x"1" ]; then
 set -x
fi

if [ x"$APPDIR" = x"" ]; then
 echo "AppRun: error: could not find mount point" >&2
 exit 127
fi


__CONTAINER_NAME=


# argument parsing  #{{{2

__parse_args() {
 local __compile_optstring="$1"; shift
 
 local __positional=1
 local __dash_dash=0
 while [ $# -gt 0 ]; do
  if [ $__dash_dash -eq 0 ]; then
   local __dash_dash_pos=-1; local i=1
   for arg; do
    if [ x"$arg" = x"--" ]; then
     __dash_dash_pos=$i
     break
    fi
    i=$(($i + 1))
   done
   OPTIND=1
   while getopts "$__compile_optstring" __compile_opt; do
    if [ x"$__compile_opt" = x"?" ]; then
     exit 2
    fi
    __COMPILE_ARG_VALUE=$OPTARG
    unset OPTARG
    eval "__config_flag_arg_$__compile_opt"
    OPTARG=$__COMPILE_ARG_VALUE
   done
  fi
  if [ $__dash_dash -eq 0 ] && [ $OPTIND -eq $(($__dash_dash_pos + 1)) ]; then
   __dash_dash=1
   shift $((OPTIND - 1))
  elif [ $OPTIND -eq 1 ]; then
   __COMPILE_ARG_VALUE=$1
   eval "__config_pos_arg_$__positional"
   shift
   __positional=$(($__positional + 1))
  else
   shift $(($OPTIND - 1))
  fi
  unset __COMPILE_ARG_VALUE __COMPILE_OPTIND OPTARG
 done
}


# fill-ins  #{{{2

# miscellaneous  #{{{3

___config_misc___


# arguments  #{{{3

___config_args___


# environment  #{{{3

___config_env___


# binds  #{{{3

___config_binds___


# bundle init  #{{{2
#export SINGULARITY_ARGV0="${ARGV0:-$0}"

if [ x"$__CONTAINER_NAME" = x"" ]; then
 __CONTAINER_NAME=elements-$(mktemp -u XXXXXX)$(mktemp -u XXXXXX)
fi

BUNDLE=$(mktemp -d /tmp/.elements-ctr.XXXXXX); r=$?
if [ $r -ne 0 ]; then
 echo "AppRun: error: could not make bundle directory (mktemp error $r)" >&2
 exit 127
fi

cleanup() {
 rm -rf "$BUNDLE"
}

trap 'cleanup' INT TERM 0

runc spec -b "$BUNDLE" --rootless
printf '%s\n' "$APPDIR" > "$BUNDLE/appdir"
printf '%s\n' "$__CONTAINER_NAME" > "$BUNDLE/name"


# prepare bootstrap environment  #{{{2

(cd "$BUNDLE" && tar -xf "$APPDIR/bootstrap.tar")
rm -f "$BUNDLE/bootstrap.def"

# disable terminal and readonly rootfs
awk '
 BEGIN { terminal = 0; ro = 0 };
 /"terminal":[ \t]*true/ {
  if (!terminal) {
   sub(/"terminal":[ \t]*true/, "\"terminal\": false");
   terminal = 1;
  }
 };
 /"readonly":[ \t]*true/ {
  if (!ro) {
   sub(/"readonly":[ \t]*true/, "\"readonly\": false");
   ro = 1;
  }
 };
 { print }
' "$BUNDLE/config.json" > "$BUNDLE/config.tmp"
mv "$BUNDLE/config.tmp" "$BUNDLE/config.json"

escape_args() {
 printf "'"; printf '%s' "$1" | sed -e "s/'/'\\\\''/g"; printf "'"
 shift
 for i; do
  printf ' '
  printf "'"; printf '%s' "$i" | sed -e "s/'/'\\\\''/g"; printf "'"
 done
}

run_bootstrap() {
 set +e
 escape_args "$@" | runc run --no-pivot -b "$BUNDLE" \
  "$__CONTAINER_NAME.$(mktemp -u bootstrap.XXXXXX)"
 local r=$?
 set -e
 return $r
}

abspath() {
 printf '%s\n' \
  "$(cd "$(dirname -- "$1")"; printf '%s' "$(pwd)")/$(basename -- "$1")"
}


# configure container  #{{{2

_jq() {
 cp "$BUNDLE/final.json" "$BUNDLE/rootfs/final.json"
 set +e
 run_bootstrap jq "$@" "/final.json" > "$BUNDLE/tmp.json"
 set -e
 mv "$BUNDLE/tmp.json" "$BUNDLE/final.json"
}

cp "$BUNDLE/config.json" "$BUNDLE/final.json"

config_misc
config_args "$@"
config_env
config_binds

basic_mounts='{
 "destination": "/tmp",
 "type": "tmpfs",
 "source": "tmpfs",
 "options": ["nosuid", "nodev", "size=16384k"]
}'

if [ $__CONFIG_RESOLV -ne 0 ] && [ -f /etc/resolv.conf ]; then
 basic_mounts="$basic_mounts,"'{
  "destination": "/etc/resolv.conf",
  "type": "bind",
  "source": "/etc/resolv.conf",
  "options": ["rbind"]
 }'
fi

_jq '.mounts |= . + ['"$basic_mounts"']'

_jq \
 --arg cmd "/.elements-entry" \
 --argjson terminal $__CONFIG_TERMINAL \
 --arg hostname "$(hostname 2>/dev/null | echo "${HOSTNAME:-Elements}")" \
 '.process.args[0]=$cmd | .process.terminal=$terminal | .hostname=$hostname'

_jq --arg rootfs "$APPDIR/rootfs" '.root.path=$rootfs | .root.readonly=false'


# cleanup bootstrap environment  #{{{2
rm -rf "$BUNDLE/rootfs"


# run container  #{{{2

mv "$BUNDLE/final.json" "$BUNDLE/config.json"
runc run -b "$BUNDLE" "$__CONTAINER_NAME"
r=$?


# cleanup container and exit  #{{{2

cleanup
exit $r
