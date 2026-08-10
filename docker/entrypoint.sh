#!/usr/bin/env sh
# One image, two roles. The *command* selects which: `api` serves HTTP, `ingest`
# indexes configured sources and exits. Config comes from the environment.
set -eu

case "${1:-api}" in
  api)
    exec twin serve
    ;;
  ingest)
    shift
    exec twin ingest "$@"
    ;;
  *)
    # Anything else: run it verbatim (e.g. a shell for debugging).
    exec "$@"
    ;;
esac
