#!/bin/bash
set -euo pipefail

# load .env variables
[ -f .env ] && export $(grep -v '^#' .env | xargs)

# config
input_file="curl.txt"
output_curl="export_curl.txt"
output_fail="export_curl_fail.log"
ENABLE_REPORT=0
output_report="export_curl_report.csv"
baseurl="http://127.0.0.1:8000"
token_root="${config_key_root:-}"
token="${token:-}"

# initialize report and curl output files
[ "$ENABLE_REPORT" -eq 1 ] && echo "API,Status Code,Response Time (ms)" > "$output_report"
: > "$output_curl"

# counters
count=0; count_success=0; count_fail=0; total_response_time=0

# read file with joined continuation lines (handles trailing spaces after '\')
while IFS= read -r line || [[ -n "$line" ]]; do
    : # noop (this loop is here to keep same structure); will be replaced by process substitution below
done < <(sed -e ':a' -e '/\\$/N; s/\\\n[[:space:]]*/ /; ta' "$input_file")

# process each joined command line
while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" != curl* ]] && continue

    # substitute variables BEFORE execution
    command_line=$(echo "$line" | sed -e "s|\$baseurl|$baseurl|g" \
                                  -e "s|\$token_root|$token_root|g" \
                                  -e "s|\$token|$token|g")

    # extract URL (first quoted string after curl)
    url=$(echo "$command_line" | sed -n 's/^curl[^"]*"\([^"]*\)".*/\1/p')
    echo "🚀 $url"

    # pretty-print into export_curl.txt (each flag on its own line, with backslashes)
    echo "$command_line" | sed \
      -e 's/ -H / \\\n  -H /g' \
      -e 's/ -d / \\\n  -d /g' \
      -e 's/ -F / \\\n  -F /g' \
      -e 's/ -o / \\\n  -o /g' \
      >> "$output_curl"
    echo >> "$output_curl"

    # execute curl and capture body+writeout; do not let a non-zero exit stop the script
    # append a write-out marker on a new line to reliably parse status and time
    out_and_write=$(bash -c "$command_line --silent --show-error --write-out '\n%{http_code} %{time_total}'" 2>&1 || true)

    # last line is "HTTPCODE TIMETOTAL"
    status_time=$(printf '%s\n' "$out_and_write" | tail -n1 || true)
    status_code=$(awk '{print $1}' <<<"${status_time:-}")
    time_total=$(awk '{print $2}' <<<"${status_time:-}")
    execution_time=$(awk -v t="${time_total:-0}" 'BEGIN{printf("%d", t*1000)}')

    # body = everything except the last line
    body=$(printf '%s\n' "$out_and_write" | sed '$d' 2>/dev/null || true)
    [ -z "$body" ] && body="(empty response)"

    # update counters and report
    total_response_time=$((total_response_time + execution_time))
    ((count++))
    [ "$ENABLE_REPORT" -eq 1 ] && echo "$url,$status_code,$execution_time" >> "$output_report"

    # handle success or failure
    if [[ "$status_code" -eq 200 ]]; then
        echo "✅ Success (${execution_time}ms)"
        ((count_success++))
    else
        echo "❌ $body"
        # create file only on first failure
        if [[ $count_fail -eq 0 ]]; then
            : > "$output_fail"
        fi
        {
            echo "$command_line"
            echo "$body"
            echo
        } >> "$output_fail"
        ((count_fail++))
    fi

    echo
done < <(sed -e ':a' -e '/\\$/N; s/\\\n[[:space:]]*/ /; ta' "$input_file")

# summary
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
