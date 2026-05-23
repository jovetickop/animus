#!/bin/bash
# Format edited C/C++ files after Claude Code write operations.

input=$(cat)
file_path=$(echo "$input" | sed -n 's/.*"file_path":"\([^"]*\)".*/\1/p')

[ -z "$file_path" ] && exit 0

file_path="${file_path//\\//}"

case "$file_path" in
    *.cpp|*.cc|*.cxx|*.c|*.h|*.hpp|*.hxx) ;;
    *) exit 0 ;;
esac

if command -v clang-format >/dev/null 2>&1; then
    clang-format -i "$file_path"
    echo "[clang-format] formatted: $file_path"
fi
