all: elements
.PHONY: version test

define __version :=
	v=$$(git describe --tags --dirty --always 2>/dev/null || echo 'vUNKNOWN'); \
	v=$$(printf '%s\n' "$${v#v}" | sed -e \
         's/-\([0-9]\+\?-g[a-fA-F0-9]\{7\}\)/+\1/; s/-\(g[a-fA-F0-9]\{7\}\|dirty\)/.\1/g');
endef

version:
	@$(__version) \
	 printf '%s\n' "$$v"

elements: src/elements.tpl.py src/loader.tpl.sh
	mypy "$<"
	$(__version) \
	python3 -c \
	 '1; \
	  import sys; argv = sys.argv; \
	  src = open(argv[1], "rb"); \
	  loader_tpl = open(argv[2], "rb"); \
	  license = open(argv[3], "rb"); \
	  r = src.read().replace(b"___LOADER_TPL___", loader_tpl.read()); \
	  r = r.replace(b"___LICENSE___", license.read()); \
	  r = r.replace(b"___VERSION___", argv[4].encode("utf-8")); \
	  license.close(); loader_tpl.close(); src.close(); \
	  sys.stdout.buffer.write(r); sys.stdout.buffer.flush(); \
	 ' \
	 "$<" \
	 "src/loader.tpl.sh" \
	 "LICENSE.txt" \
	 "$$v" > "$@"; \
	 r=$$?; [ $$r -ne 0 ] && rm -f "$@" || true
	chmod +x "$@"


# Manual testing

TEST_ELEMENT := test/parsing


${TEST_ELEMENT}/element: elements ${TEST_ELEMENT}/element.def
	sudo "./$<" "${TEST_ELEMENT}/element.def" "$@"


test: ${TEST_ELEMENT}/element
	[ x"${debug}" = x"1" ] && export __ELEMENTS_CTR_DEBUG=1 || true; \
	[ x"${dash}" = x"0" ] && true || export __ELEMENTS_USE_DASH=1; \
	 instance=from-make+%; \
	 \
	 env HOST_VAR=1234 TRUTHY=yes FALSY=0 EMPTY= YOUR_FACE=no \
	  "./$<" \
	   -v "${TEST_ELEMENT}/docroot" -H spam 2629 \
	   -d "${TEST_ELEMENT}/data" -n "$$instance"
