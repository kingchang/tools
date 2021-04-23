#!/bin/sh

# Starts Liferea in the background and minimizes it.
# https://github.com/lwindolf/liferea/issues/447
#
# Arguments: passthrough to Liferea
# Stdin: none
# Stdout: none
#
# Runtime dependencies:
#   apt install liferea # Version: 1.13.1-1
#   apt install xdotool # Version: 1:3.20160805.1-4
#
# Test dependencies:
#   apt install shellcheck # Version: 0.7.1-1build1

set -e -u

LIFEREA_BIN="${LIFEREA_BIN:-liferea}"
XDOTOOL_BIN="${XDOTOOL_BIN:-xdotool}"

# Search for a visible window by class name.
#
# Globals: XDOTOOL_BIN
# Arguments: (pass-through)
# Stdin: none
# Stdout: search results
xdotool_search() {
    "$XDOTOOL_BIN" search --onlyvisible --classname "$@"
}

if ! command -v "$LIFEREA_BIN" >/dev/null; then
    echo "Error: $LIFEREA_BIN not found (override \$LIFEREA_BIN)" >&2
    exit 1
fi

if ! command -v "$XDOTOOL_BIN" >/dev/null; then
    echo "Error: $XDOTOOL_BIN not found (override \$XDOTOOL_BIN)" >&2
    exit 1
fi

classname=Liferea

# TODO: possible race-condition
if ! xdotool_search "$classname" windowminimize >/dev/null; then
    # TODO: output from Liferea, including these scripts will litter tty/stdout
    "$LIFEREA_BIN" "$@" &
    exit_status=$?

    xdotool_search --sync "$classname" windowminimize
    exit $exit_status
fi
