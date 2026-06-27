#!/bin/bash
# Format edited C/C++ files after Claude Code write operations.

input=$(cat)
# 使用 jq 解析 JSON（含 Python fallback）
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
if [ -z "$file_path" ] && command -v python >/dev/null 2>&1; then
    file_path=$(echo "$input" | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)
fi
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
