#!/bin/bash

# env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

#env var
baseurl="http://127.0.0.1:8000"
token_root="$key_root"
token_admin="$token_admin"
file_create="$file_create"
file_update="$file_update"
file_delete="$file_delete"
output_file="$output_file"

#fixed var
input_file="curl.txt"
uuid_1="$(uuidgen | tr '[:upper:]' '[:lower:]')"
uuid_2="$(uuidgen | tr '[:upper:]' '[:lower:]')"

# Initialize CSV file with headers
echo "API,Status Code,Response Time (ms)" > "$output_file"

# Count variables
count=0
count_success=0
count_fail=0
total_response_time=0  # To calculate average response time

# Check if gdate (GNU date) is installed for nanosecond support
if command -v gdate &>/dev/null; then
    DATE_CMD="gdate"
else
    DATE_CMD="date"
fi

# Read the curl commands from the file and process each line
while IFS= read -r line; do
    # Check if the line contains a curl command
    if [[ "$line" == curl* ]]; then
        # Replace the placeholders with actual variable values
        command=$(echo "$line" | sed -e "s|\$baseurl|$baseurl|g" \
                             -e "s|\$token_root|$token_root|g" \
                             -e "s|\$token_admin|$token_admin|g" \
                             -e "s|\$username|$uuid_1|g" \
                             -e "s|\$username_2|$uuid_2|g" \
                             -e "s|\$file_create|$file_create|g" \
                             -e "s|\$file_update|$file_update|g" \
                             -e "s|\$file_delete|$file_delete|g"
                             )
        # Extract and print only the URL for readability
        url=$(echo "$command" | sed -n 's/^curl -X [A-Z]* "\([^"]*\)".*/\1/p')
        echo "🚀 $url"

        # Start time (use nanoseconds if gdate is available, otherwise fallback to seconds)
        if [ "$DATE_CMD" == "gdate" ]; then
            start_time=$($DATE_CMD +%s%N)  # Nanoseconds timestamp using gdate
        else
            start_time=$($DATE_CMD +%s)  # Seconds timestamp on macOS without gdate
        fi

        # Run the curl command, capturing both response body and status code
        response=$(eval "$command -s -w '\n%{http_code}'")

        # End time (use nanoseconds if gdate is available, otherwise fallback to seconds)
        if [ "$DATE_CMD" == "gdate" ]; then
            end_time=$($DATE_CMD +%s%N)  # Nanoseconds timestamp using gdate
            execution_time=$(( (end_time - start_time) / 1000000 ))  # Convert to ms
        else
            end_time=$($DATE_CMD +%s)  # Seconds timestamp on macOS without gdate
            execution_time=$(( (end_time - start_time) * 1000 ))  # Convert to ms
        fi

        total_response_time=$((total_response_time + execution_time))  # Accumulate response time

        # Extract HTTP status code (last line of response)
        status_code=$(echo "$response" | awk 'END {print}')

        # Extract response body (all lines except the last one)
        body=$(echo "$response" | sed '$d')

        # Increment the counter
        ((count++))

        # Log results in CSV file
        echo "$url,$status_code,$execution_time" >> "$output_file"

        # Check response status
        if [[ "$status_code" -eq 200 ]]; then
            echo -e "✅ Success (${execution_time}ms)\n"
             # echo "📄 (${body})"
            ((count_success++))
        else
            echo -e "❌ $body\n"
            ((count_fail++))
        fi
    else
        # If it's not a curl command, skip it
        continue
    fi
done < "$input_file"

# Calculate average response time (avoid division by zero)
if [[ $count -gt 0 ]]; then
    avg_response_time=$((total_response_time / count))
else
    avg_response_time=0
fi

# Final summary message
echo "--------------------------------------"
echo "📊 API Execution Summary"
echo "🚀 Total: $count"
echo "✅ Success: $count_success"
echo "❌ Fail: $count_fail"
echo "⏳ Avg Response Time: ${avg_response_time}ms"
echo "📄 Results saved in: $output_file"
echo "--------------------------------------"
