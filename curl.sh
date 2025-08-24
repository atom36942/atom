#!/bin/bash
set -euo pipefail

[ -f .env ] && export $(grep -v '^#' .env | xargs)

# Variables
input_file="curl.txt"
baseurl="http://127.0.0.1:8000"
token_root="${config_key_root:-}"
token="${token:-}"
username="$(uuidgen | tr '[:upper:]' '[:lower:]')"
output_file="export_curl_report.csv"
output_curl="export_curl_full.txt"
output_fail="export_curl_fail.log"
ENABLE_REPORT=0
query="select * from users limit 10;"

# Initialize files
[ "$ENABLE_REPORT" -eq 1 ] && echo "API,Status Code,Response Time (ms)" > "$output_file"
: > "$output_curl"
: > "$output_fail"

count=0; count_success=0; count_fail=0; total_response_time=0

while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" != curl* ]] && continue

    # Replace placeholders
    command_line=$(echo "$line" | sed -e "s|\$baseurl|$baseurl|g" \
                                      -e "s|\$token_root|$token_root|g" \
                                      -e "s|\$token|$token|g" \
                                      -e "s|\$username|$username|g" \
                                      -e "s|\$query|$query|g")

    url=$(echo "$command_line" | sed -n 's/^curl[^"]*"\([^"]*\)".*/\1/p')
    echo "🚀 $url"

    # Save multi-line curl for Postman
    echo "$command_line" | sed 's/ -H / \\\n  -H /g; s/ -d / \\\n  -d /g' >> "$output_curl"
    echo >> "$output_curl"

    response_file=$(mktemp)

    # Execute full command safely with bash -c, capture stdout/stderr
    status_time=$(bash -c "$command_line -s -o \"$response_file\" -w '%{http_code} %{time_total}'" 2>&1)
    status_code=$(echo "$status_time" | awk '{print $1}')
    time_total=$(echo "$status_time" | awk '{print $2}')
    execution_time=$(awk -v t="$time_total" 'BEGIN{printf("%d", t*1000)}')

    total_response_time=$((total_response_time + execution_time))
    ((count++))
    [ "$ENABLE_REPORT" -eq 1 ] && echo "$url,$status_code,$execution_time" >> "$output_file"

    # Read response body
    body=$(<"$response_file")
    [ -z "$body" ] && body="(empty response)"

    if [[ "$status_code" -eq 200 ]]; then
        echo "✅ Success (${execution_time}ms)"
        ((count_success++))
    else
        echo "❌ $body"
        # Log failure with blank line
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
[ "$ENABLE_REPORT" -eq 1 ] && echo "📄 Results saved in: $output_file"
echo "📄 Full curl commands saved in: $output_curl"
if [[ $count_fail -gt 0 ]]; then
    echo "📄 Failed responses saved in: $output_fail"
fi
echo "--------------------------------------"
