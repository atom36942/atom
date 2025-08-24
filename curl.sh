#!/bin/bash
set -euo pipefail

[ -f .env ] && export $(grep -v '^#' .env | xargs)

input_file="curl.txt"
baseurl="http://127.0.0.1:8000"
token_root="${config_key_root:-}"
token="${token:-}"
username="$(uuidgen | tr '[:upper:]' '[:lower:]')"
output_curl="export_curl.txt"
output_fail="export_curl_fail.log"
output_report="export_curl_report.csv"
ENABLE_REPORT=0
query="select * from users limit 10;"

[ "$ENABLE_REPORT" -eq 1 ] && echo "API,Status Code,Response Time (ms)" > "$output_report"
: > "$output_curl"

count=0; count_success=0; count_fail=0; total_response_time=0

while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" != curl* ]] && continue

    command_line=$(echo "$line" | sed -e "s|\$baseurl|$baseurl|g" \
                                      -e "s|\$token_root|$token_root|g" \
                                      -e "s|\$token|$token|g" \
                                      -e "s|\$username|$username|g" \
                                      -e "s|\$query|$query|g")

    url=$(echo "$command_line" | sed -n 's/^curl[^"]*"\([^"]*\)".*/\1/p')
    echo "🚀 $url"

    echo "$command_line" | sed 's/ -H / \\\n  -H /g; s/ -d / \\\n  -d /g' >> "$output_curl"
    echo >> "$output_curl"

    response_file=$(mktemp)
    status_time=$(bash -c "$command_line -s -o \"$response_file\" -w '%{http_code} %{time_total}'" 2>&1)
    status_code=$(echo "$status_time" | awk '{print $1}')
    time_total=$(echo "$status_time" | awk '{print $2}')
    execution_time=$(awk -v t="$time_total" 'BEGIN{printf("%d", t*1000)}')

    total_response_time=$((total_response_time + execution_time))
    ((count++))
    [ "$ENABLE_REPORT" -eq 1 ] && echo "$url,$status_code,$execution_time" >> "$output_report"

    body=$(<"$response_file")
    [ -z "$body" ] && body="(empty response)"

    if [[ "$status_code" -eq 200 ]]; then
        echo "✅ Success (${execution_time}ms)"
        ((count_success++))
    else
        echo "❌ $body"
        # Create file only on first failure
        if [[ $count_fail -eq 0 ]]; then
            : > "$output_fail"
        fi
        {
            echo "🚀 $url"
            echo "❌ $body"
            echo
        } >> "$output_fail"
        ((count_fail++))
    fi

    rm -f "$response_file"
    echo
done < "$input_file"

avg_response_time=$(( count>0 ? total_response_time/count : 0 ))
echo "--------------------------------------"
echo "📊 API Execution Summary"
echo "🚀 Total: $count"
echo "✅ Success: $count_success"
echo "❌ Fail: $count_fail"
echo "⏳ Avg Response Time: ${avg_response_time}ms"
[ "$ENABLE_REPORT" -eq 1 ] && echo "📄 Results saved in: $output_report"
echo "📄 Full curl commands saved in: $output_curl"
[[ $count_fail -gt 0 ]] && echo "📄 Failed responses saved in: $output_fail"
echo "--------------------------------------"
