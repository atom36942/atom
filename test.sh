#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)

#config
input_path="$SCRIPT_DIR/curl.txt"
outpath_path="$SCRIPT_DIR/export/curl_output.txt"
outpath_path_fail="$SCRIPT_DIR/export/curl_fail.log"
baseurl="http://127.0.0.1:8000"
token_root="${config_key_root:-}"
token="${token:-}"
uuid=$(uuidgen)
username=$(python3 -c "import random, string; print(random.choice(string.ascii_lowercase) + ''.join(random.choices(string.ascii_lowercase + string.digits, k=11)))")
username_bigint=$(python3 -c "import random; print(random.randint(10**15, 10**18))")

#logic
if [ ! -f "$input_path" ]; then
    echo "❌ Input file not found: $input_path"
    exit 1
fi
mkdir -p "$SCRIPT_DIR/export"
: > "$outpath_path"
count=0; count_success=0; count_fail=0; total_response_time=0
while IFS= read -r line || [[ -n "$line" ]]; do
    :
done < <(sed -e ':a' -e '/\\$/N; s/\\\n[[:space:]]*/ /; ta' "$input_path")
while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" != curl* ]] && continue
    command_line=$(echo "$line" | sed -e "s|\$baseurl|$baseurl|g" \
                              -e "s|\$token_root|$token_root|g" \
                              -e "s|\$token|$token|g" \
                              -e "s|\$uuid|$uuid|g" \
                              -e "s|\$username_bigint|$username_bigint|g" \
                              -e "s|\$username|$username|g")
    url=$(echo "$command_line" | sed -n 's/^curl[^"]*"\([^"]*\)".*/\1/p')
    echo "🚀 $url"
    echo "$command_line" | sed \
      -e 's/ -H / \\\n  -H /g' \
      -e 's/ -d / \\\n  -d /g' \
      -e 's/ -F / \\\n  -F /g' \
      -e 's/ -o / \\\n  -o /g' \
      >> "$outpath_path"
    echo >> "$outpath_path"
    out_and_write=$(bash -c "$command_line --silent --show-error --write-out '\n%{http_code} %{time_total}'" 2>&1 || true)
    status_time=$(printf '%s\n' "$out_and_write" | tail -n1 || true)
    status_code=$(awk '{print $1}' <<<"${status_time:-}")
    time_total=$(awk '{print $2}' <<<"${status_time:-}")
    execution_time=$(awk -v t="${time_total:-0}" 'BEGIN{printf("%d", t*1000)}')
    body=$(printf '%s\n' "$out_and_write" | sed '$d' 2>/dev/null || true)
    [ -z "$body" ] && body="(empty response)"
    total_response_time=$((total_response_time + execution_time))
    ((count++))
    if [[ "$status_code" -eq 200 ]]; then
        echo "✅ Success (${execution_time}ms)"
        ((count_success++))
    else
        echo "❌ $body"
        if [[ $count_fail -eq 0 ]]; then
            : > "$outpath_path_fail"
        fi
        {
            echo "$command_line"
            echo "$body"
            echo
        } >> "$outpath_path_fail"
        ((count_fail++))
    fi
    echo
done < <(sed -e ':a' -e '/\\$/N; s/\\\n[[:space:]]*/ /; ta' "$input_path")

# summary
avg_response_time=$(( count>0 ? total_response_time/count : 0 ))
echo "--------------------------------------"
echo "📊 Curl Execution Summary"
echo "🚀 Total: $count"
echo "✅ Success: $count_success"
echo "❌ Fail: $count_fail"
echo "⏳ Avg Response Time: ${avg_response_time}ms"
echo "📄 Report : $outpath_path"
[[ $count_fail -gt 0 ]] && echo "📄 Failed responses saved in: $outpath_path_fail"
echo "--------------------------------------"