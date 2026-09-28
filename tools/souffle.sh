#!/bin/sh
# Wrapper for the locally unpacked Soufflé 2.5 (ubuntu-2404 .deb, no root install).
D="$(cd "$(dirname "$0")" && pwd)/souffle"
LD_LIBRARY_PATH="$D/usr/lib:$D/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH" exec "$D/usr/bin/souffle" "$@"
