#!/bin/sh
# vim: set fdm=marker fdl=1 sw=1:

# version: ___VERSION___

# script setup  #{{{2

ELEMENTS_MAGIC=Elements

ELEMENTS_ID=
ELEMENTS_INSTANCE=
ELEMENTS_NAME=


set -e

if [ x"$__ELEMENTS_CTR_DEBUG" = x"1" ]; then
 set -x
fi


if [ x"$APPDIR" = x"" ]; then
 echo "elements: error: could not find mount point" >&2
 exit 127
fi

if [ x"$ARGV0" = x"" ]; then
 ARGV0=element
fi


STATE_ROOT="/tmp/.elements-ctr-u$(id -u)"
if [ x"$XDG_RUNTIME_DIR" != x"" ] && [ -d "$XDG_RUNTIME_DIR" ]; then
 XDG_STATE_ROOT="$XDG_RUNTIME_DIR/elements"
 if [ -e "$XDG_STATE_ROOT" ]; then
  if [ -d "$XDG_STATE_ROOT" ] && [ -r "$XDG_STATE_ROOT/.@magic" ] && \
     [ x"$(cat "$XDG_STATE_ROOT/.@magic" || true)" = x"$ELEMENTS_MAGIC" ]; then
   STATE_ROOT=$XDG_STATE_ROOT
  fi
 else
  STATE_ROOT=$XDG_STATE_ROOT
 fi
fi

mkdir -m 0700 -p "$STATE_ROOT"
chmod 1700 "$STATE_ROOT"  # prevent auto-pruning per XDG spec
if ! [ -e "$STATE_ROOT/.@magic" ]; then
 printf '%s\n' "$ELEMENTS_MAGIC" > "$STATE_ROOT/.@magic"
 chmod 0600 "$STATE_ROOT/.@magic"
fi

SHM_ROOT="/dev/shm/elements-u$(id -u)"


BOOTSTRAP_BUNDLE=
FINAL_BUNDLE=
SHM_DIR=

cleanup() {
 if [ x"$BOOTSTRAP_BUNDLE" != x"" ] && [ -d "$BOOTSTRAP_BUNDLE" ]; then
  rm -rf "$BOOTSTRAP_BUNDLE" || true
 fi
 if [ x"$FINAL_BUNDLE" != x"" ] && [ -d "$FINAL_BUNDLE" ]; then
  "$APPDIR/elements-cleanup.sh" "$FINAL_BUNDLE" || true
 fi
 if [ x"$SHM_DIR" != x"" ] && [ -d "$SHM_DIR" ]; then
  rm -rf "$SHM_DIR" || true
 fi
}

trap 'cleanup' INT TERM 0


random_12() {
 printf '%s\n' "$(mktemp -u XXXXXX)$(mktemp -u XXXXXX)"
}


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

BOOTSTRAP_BUNDLE=$(mktemp -d "$STATE_ROOT/.@bootstrap.XXXXXX"); r=$?
if [ $r -ne 0 ]; then
 echo "elements: error: could not make bootstrap directory (mktemp error $r)" >&2
 exit 127
fi
chmod 0700 "$BOOTSTRAP_BUNDLE"

runc spec -b "$BOOTSTRAP_BUNDLE" --rootless


# prepare bootstrap environment  #{{{2

(cd "$BOOTSTRAP_BUNDLE" && tar -xf "$APPDIR/bootstrap.tar")
rm -f "$BOOTSTRAP_BUNDLE/bootstrap.def"

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
' "$BOOTSTRAP_BUNDLE/config.json" > "$BOOTSTRAP_BUNDLE/config.tmp"
mv "$BOOTSTRAP_BUNDLE/config.tmp" "$BOOTSTRAP_BUNDLE/config.json"

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
 escape_args "$@" | runc run --no-pivot -b "$BOOTSTRAP_BUNDLE" \
  "__elements-bootstrap.$__CONFIG_NAME.$(random_12)"
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
 cp "$BOOTSTRAP_BUNDLE/final.json" "$BOOTSTRAP_BUNDLE/rootfs/final.json"
 set +e
 run_bootstrap jq "$@" "/final.json" > "$BOOTSTRAP_BUNDLE/tmp.json"
 set -e
 mv "$BOOTSTRAP_BUNDLE/tmp.json" "$BOOTSTRAP_BUNDLE/final.json"
}

cp "$BOOTSTRAP_BUNDLE/config.json" "$BOOTSTRAP_BUNDLE/final.json"

config_misc
config_args "$@"
config_env
config_binds

if ! (printf '%s\n' "$ELEMENTS_NAME" | grep -q -e '^[0-9a-zA-Z_+.-]\+$'); then
 echo "elements: error: \`$ELEMENTS_NAME\` is not a valid container app name" >&2
 exit 2
fi
if ! (printf '%s\n' "$ELEMENTS_INSTANCE" | grep -q -e '^[%0-9a-zA-Z_+.-]*$'); then
 echo "elements: error: \`$ELEMENTS_INSTANCE\` is not a valid instance ID" >&2
 exit 2
fi

ELEMENTS_INSTANCE=$(printf '%s\n' "${ELEMENTS_INSTANCE:-%}" |
 awk -v random_12="$(random_12)" \
 '{ gsub(/%/, random_12); print }')

ELEMENTS_ID="$ELEMENTS_NAME.$ELEMENTS_INSTANCE"
FINAL_BUNDLE_PATH="$STATE_ROOT/$ELEMENTS_ID"
SHM_DIR_PATH="$SHM_ROOT/$ELEMENTS_ID"

_jq \
 --arg env_magic "ELEMENTS_MAGIC=$ELEMENTS_MAGIC" \
 --arg env_instance "ELEMENTS_INSTANCE=$ELEMENTS_INSTANCE" \
 --arg env_id "ELEMENTS_ID=$ELEMENTS_ID" \
 --arg env_term "TERM=${TERM:-xterm}" \
 '.process.env |= (. | map(select(.|startswith("TERM=")|not))) + [
  $env_magic,
  $env_instance,
  $env_id,
  $env_term
 ]'


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


if ! [ -t 0 ]; then
 __CONFIG_TERMINAL=false
fi

RUNC_ROOTFS="$APPDIR/rootfs"
JQ_SHM_PATH=
if [ $__CONFIG_ROOT_COPYUP -ne 0 ]; then
 RUNC_ROOTFS="$SHM_DIR_PATH/copyup"
 JQ_SHM_PATH=$SHM_DIR_PATH
fi

_jq \
 --arg cmd "/.elements-entry" \
 --argjson terminal $__CONFIG_TERMINAL \
 --arg hostname "$(hostname 2>/dev/null || echo "${HOSTNAME:-Elements}")" \
 --arg rootfs "$RUNC_ROOTFS" \
 --arg cleanup "$APPDIR/elements-cleanup.sh" \
 --arg bundle "$FINAL_BUNDLE_PATH" \
 --arg shm "$JQ_SHM_PATH" \
 '
  .process.args[0]=$cmd |
  .process.terminal=$terminal |
  .hostname=$hostname |
  .root.path=$rootfs |
  .root.readonly=false |
  (.hooks.poststop |= . + [{
   "path": $cleanup,
   "args": ["elements-cleanup.sh", $bundle, $shm]
  }])
 '


# cleanup bootstrap environment  #{{{2

rm -rf "$BOOTSTRAP_BUNDLE/rootfs"


# prepare final bundle  #{{{2

if [ -e "$FINAL_BUNDLE_PATH" ]; then
 echo "elements: error: a container with ID \`$ELEMENTS_ID\` already exists" >&2
 exit 127
fi
mkdir -m 0700 "$FINAL_BUNDLE_PATH"
FINAL_BUNDLE=$FINAL_BUNDLE_PATH

printf '%s\n' "$ELEMENTS_MAGIC" > "$FINAL_BUNDLE/magic"
printf '%s\n' "$ELEMENTS_NAME" > "$FINAL_BUNDLE/name"
printf '%s\n' "$ELEMENTS_INSTANCE" > "$FINAL_BUNDLE/instance"
printf '%s\n' "$ELEMENTS_ID" > "$FINAL_BUNDLE/id"
ln -s "$APPDIR" "$FINAL_BUNDLE/appdir"

if [ $__CONFIG_ROOT_COPYUP -ne 0 ]; then
 mkdir -m 0700 -p "$SHM_ROOT"
 mkdir -m 0700 "$SHM_DIR_PATH"
 SHM_DIR=$SHM_DIR_PATH
 ln -s "$SHM_DIR" "$FINAL_BUNDLE/shm"
 cp -pPR "$APPDIR/rootfs" "$SHM_DIR/copyup"
 chmod 0700 "$SHM_DIR/copyup"
fi

mv "$BOOTSTRAP_BUNDLE/final.json" "$FINAL_BUNDLE/config.json"

rm -rf "$BOOTSTRAP_BUNDLE"
BOOTSTRAP_BUNDLE=


# run container  #{{{2

exec runc run \
 --pid-file "$FINAL_BUNDLE/pid" \
 -b "$FINAL_BUNDLE" \
 "$ELEMENTS_ID"
