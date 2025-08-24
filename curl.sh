#!/bin/bash
set -euo pipefail

[ -f .env ] && export $(grep -v '^#' .env | xargs)

input_file="curl.txt"
baseurl="http://127.0.0.1:8000"
token_root="${config_key_root:-}"
token="${token:-}"
username="$(uuidgen | tr '[:upper:]' '[:lower:]')"
output_file="export_curl_report.csv"
output_curl="export_curl_full.txt"   # <<< new
ENABLE_REPORT=0

[ "$ENABLE_REPORT" -eq 1 ] && echo "API,Status Code,Response Time (ms)" > "$output_file"
echo "" > "$output_curl"   # clear file each run

count=0; count_success=0; count_fail=0; total_response_time=0

while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" != curl* ]] && continue

    command=$(echo "$line" | sed -e "s|\$baseurl|$baseurl|g" \
                                 -e "s|\$token_root|$token_root|g" \
                                 -e "s|\$token|$token|g" \
                                 -e "s|\$username|$username|g")

    url=$(echo "$command" | sed -n 's/^curl[^"]*"\([^"]*\)".*/\1/p')
    echo "🚀 $url"

    # <<< Save exact curl for Postman
    echo "$command" >> "$output_curl"

    read -r status_code time_total <<<$(eval "$command -s -o /dev/null -w '%{http_code} %{time_total}'")
    execution_time=$(awk -v t="$time_total" 'BEGIN{printf("%d", t*1000)}')

    total_response_time=$((total_response_time + execution_time)); ((count++))
    [ "$ENABLE_REPORT" -eq 1 ] && echo "$url,$status_code,$execution_time" >> "$output_file"

    if [[ "$status_code" -eq 200 ]]; then
        echo "✅ Success (${execution_time}ms)"
        ((count_success++))
    else
        echo "❌ Fail (HTTP $status_code)"
        ((count_fail++))
    fi
    echo
done < "$input_file"

avg_response_time=$(( count>0 ? total_response_time/count : 0 ))
echo "--------------------------------------"
echo "📊 API Execution Summary"
echo "🚀 Total: $count"
echo "✅ Success: $count_success"
echo "❌ Fail: $count_fail"
echo "⏳ Avg Response Time: ${avg_response_time}ms"
echo "📄 Results saved in: $output_file"
echo "📄 Full curl commands saved in: $output_curl"   # <<< new
echo "--------------------------------------"
