#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-/Users/atom/atom/.env}"
[[ -f "$ENV_FILE" ]] || { echo "ERROR: environment file not found: $ENV_FILE"; exit 2; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

required_vars=(config_postgres_url_tradelane config_clickhouse_url_tradelane)
for variable in "${required_vars[@]}"; do
  [[ -n "${!variable:-}" ]] || { echo "ERROR: $variable is missing from $ENV_FILE"; exit 2; }
done

PYTHON_BIN="${PYTHON_BIN:-/Users/atom/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"
[[ -x "$PYTHON_BIN" ]] || { echo "ERROR: Python runtime not found: $PYTHON_BIN"; exit 2; }

parse_connection_url() {
  "$PYTHON_BIN" - "$1" "$2" <<'PY'
import sys
from urllib.parse import unquote, urlparse

url = urlparse(sys.argv[1])
default_port = int(sys.argv[2])
if not all((url.hostname, url.username, url.password, url.path.strip('/'))):
    raise SystemExit('connection URL must include user, password, host, and database')
print('\t'.join((
    url.hostname,
    str(url.port or default_port),
    unquote(url.username),
    unquote(url.password),
    url.path.strip('/'),
)))
PY
}

IFS=$'\t' read -r pg_hostname pg_port PG_USER PG_PASSWORD PG_DB \
  < <(parse_connection_url "$config_postgres_url_tradelane" 5432)
IFS=$'\t' read -r CH_HOST CH_PORT CH_USER CH_PASSWORD CH_DB \
  < <(parse_connection_url "$config_clickhouse_url_tradelane" 9000)

PG_HOST="$pg_hostname:$pg_port"
PG_SCHEMA='public'
PG_URL="$config_postgres_url_tradelane"

CH_BIN="${CH_BIN:-/Users/atom/.local/bin/clickhouse}"

# The expected PostgreSQL contract and ClickHouse table definition are embedded below.
# Update both definitions deliberately whenever the shipment schema changes.
EXPECTED_COLUMN_COUNT=93

BATCH_SIZE="${BATCH_SIZE:-2000000}"
INSERT_JOBS="${INSERT_JOBS:-4}"
FILTER_JOBS="${FILTER_JOBS:-2}"
CH_MAX_THREADS="${CH_MAX_THREADS:-4}"
CH_MAX_INSERT_THREADS="${CH_MAX_INSERT_THREADS:-4}"
RUN_SHIPMENT_OPTIMIZE="${RUN_SHIPMENT_OPTIMIZE:-smart}"
RUN_FILTER_OPTIMIZE="${RUN_FILTER_OPTIMIZE:-1}"
if [[ $# -gt 0 ]]; then
  YEAR="$1"
else
  read -r -p 'Enter shipment year (example: 2019): ' YEAR
fi
[[ "$YEAR" =~ ^[0-9]{4}$ ]] || { echo 'ERROR: year must contain exactly four digits.'; exit 2; }

PG_TABLE="shipments_$YEAR"
CH_SHIPMENTS="shipments_$YEAR"
CH_FILTERS="filter_options_$YEAR"
STATE_ROOT="${STATE_ROOT:-/Users/atom/Documents/clickhouse_year_refresh_state}"
STATE_DIR="$STATE_ROOT/$YEAR"
STATE_FILE="$STATE_DIR/state.env"
FILTER_STATUS_FILE="$STATE_DIR/filter_status.csv"
LOG_FILE="$STATE_DIR/run.log"
mkdir -p "$STATE_DIR"

if [[ -z "${FORCE_FRESH+x}" && -t 0 ]]; then
  printf '\nRefresh mode for year %s:\n' "$YEAR"
  printf '  1) Resume saved run (starts new if no unfinished run exists)\n'
  printf '  2) Force fresh restart (discard unfinished staging only)\n'
  read -r -p 'Choose [1/2] (default 1): ' REFRESH_MODE
  case "${REFRESH_MODE:-1}" in
    1) FORCE_FRESH=0 ;;
    2) FORCE_FRESH=1 ;;
    *) echo 'ERROR: choose 1 or 2.'; exit 2 ;;
  esac
fi
FORCE_FRESH="${FORCE_FRESH:-0}"

RUNNING_PIDS=()
FILTER_PIDS=()
FILTER_COLS=()

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$*" | tee -a "$LOG_FILE"
}

psql_run() {
  PGAPPNAME="refresh_shipments_${YEAR}_to_clickhouse" psql "$PG_URL" -X -v ON_ERROR_STOP=1 "$@"
}

ch() {
  "$CH_BIN" client --host "$CH_HOST" --port "$CH_PORT" --user "$CH_USER" \
    --password "$CH_PASSWORD" --max_threads "$CH_MAX_THREADS" \
    --max_insert_threads "$CH_MAX_INSERT_THREADS" "$@"
}

exists_ch() { ch --query "EXISTS TABLE $CH_DB.$1"; }

save_state() {
  local temp="$STATE_FILE.tmp"
  {
    printf 'YEAR=%q\n' "$YEAR"
    printf 'RUN_ID=%q\n' "$RUN_ID"
    printf 'SHIP_STAGE=%q\n' "$SHIP_STAGE"
    printf 'FILTER_STAGE=%q\n' "$FILTER_STAGE"
    printf 'OLD_SHIPMENTS=%q\n' "$OLD_SHIPMENTS"
    printf 'OLD_FILTERS=%q\n' "$OLD_FILTERS"
    printf 'MIN_ID=%q\n' "$MIN_ID"
    printf 'MAX_ID=%q\n' "$MAX_ID"
    printf 'NEXT_ID=%q\n' "$NEXT_ID"
    printf 'EXPECTED_ROWS=%q\n' "$EXPECTED_ROWS"
    printf 'STATUS=%q\n' "$STATUS"
    printf 'UPDATED_AT=%q\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } > "$temp"
  mv "$temp" "$STATE_FILE"
}

stop_now() {
  echo
  for pid in "${RUNNING_PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  log "Stopped. Re-run the same command and enter year $YEAR to resume."
  exit 130
}
trap stop_now INT TERM

postgresql_source() {
  printf "postgresql('%s', '%s', '%s', '%s', '%s', '%s')" \
    "$PG_HOST" "$PG_DB" "$PG_TABLE" "$PG_USER" "$PG_PASSWORD" "$PG_SCHEMA"
}

expected_pg_schema() {
  cat <<'SCHEMA'
id	bigint	int8
quarter	text	text
week_of_year	integer	int4
mtons	numeric	numeric
teus	numeric	numeric
is_containerized	boolean	bool
is_hazmat	boolean	bool
hs_code_2_desc	text	text
hs_code_2_digit	integer	int4
hs_code_4_digit	integer	int4
hs_code_8_desc	text	text
hs_code_8_digit	integer	int4
lcl_flag	text	text
is_reefer	boolean	bool
is_roro	boolean	bool
estimated_us_value_fob	numeric	numeric
total_us_import_value	numeric	numeric
vessel_name	text	text
method_of_transportation	text	text
foreign_company_address	text	text
foreign_company_address_line_2	text	text
foreign_company_address_line_3	text	text
foreign_company_address_line_4	text	text
domestic_company_name	text	text
domestic_company_address_line_2	text	text
foreign_company_name	text	text
domestic_company_city	text	text
domestic_address	text	text
domestic_pin	text	text
customs_house_agent	text	text
ultimate_territory	text	text
ultimate_port_code	text	text
ultimate_region	text	text
us_coast	text	text
us_port	text	text
us_company_address	text	text
us_company_city	text	text
us_company_duns	text	text
us_company	text	text
us_company_sales_territory	text	text
foreign_company_city	text	text
foreign_company	text	text
notify_company	text	text
notify_company_state	text	text
oti_domestic	text	text
reporter_province	text	text
incoterm1	text	text
domestic_address_vn	text	text
domestic_company_phone	text	text
nvocc_line	text	text
nvocc_name_oti	text	text
oti_method	text	text
oti_name	text	text
scac	text	text
ship_type_level_2	text	text
date	date	date
month	integer	int4
teus_estimated	numeric	numeric
trade_direction	text	text
domestic_company_address_line_1	text	text
shipping_forwarder	text	text
us_company_state	text	text
bol_number	text	text
bol_id	text	text
master_bol_number	text	text
us_company_teu_volume	numeric	numeric
purpose	text	text
domestic_company_name_cleaned	text	text
foreign_company_name_cleaned	text	text
forwarder_name_cleaned	text	text
forwarders_sales_person_cleaned	text	text
domestic_company_city_cleaned	text	text
domestic_city_pincode_cleaned	text	text
foreign_company_city_cleaned	text	text
foreign_city_pincode_cleaned	text	text
cha_name_cleaned	text	text
commodity_group_cleaned	text	text
customer_rank_cleaned	integer	int4
trade_value_annual_usd_cleaned	numeric	numeric
incoterms_cleaned	text	text
tradelane_name_cleaned	text	text
assigned_sp_cleaned	text	text
reporter_port_cleaned	text	text
partner_port_cleaned	text	text
reporter_country_cleaned	text	text
partner_country_cleaned	text	text
foreign_company_address_line_1	text	text
container_size	text	text
ship_line_name	text	text
is_target	boolean	bool
is_mgh_presence	boolean	bool
is_20_80_domestic_company	boolean	bool
is_20_80_foreign_company	boolean	bool
SCHEMA
}

expected_low_cardinality_columns() {
  cat <<'COLUMNS'
quarter
hs_code_2_desc
hs_code_8_desc
lcl_flag
vessel_name
method_of_transportation
domestic_company_city
domestic_pin
customs_house_agent
ultimate_territory
ultimate_port_code
ultimate_region
us_coast
us_port
us_company_city
us_company_sales_territory
foreign_company_city
notify_company_state
oti_domestic
reporter_province
incoterm1
nvocc_line
nvocc_name_oti
oti_method
oti_name
scac
ship_type_level_2
trade_direction
shipping_forwarder
us_company_state
purpose
domestic_company_name_cleaned
foreign_company_name_cleaned
forwarder_name_cleaned
forwarders_sales_person_cleaned
domestic_company_city_cleaned
domestic_city_pincode_cleaned
foreign_company_city_cleaned
foreign_city_pincode_cleaned
cha_name_cleaned
commodity_group_cleaned
incoterms_cleaned
tradelane_name_cleaned
assigned_sp_cleaned
reporter_port_cleaned
partner_port_cleaned
reporter_country_cleaned
partner_country_cleaned
container_size
ship_line_name
COLUMNS
}

column_list() {
  ch --query "SELECT name FROM system.columns WHERE database='$CH_DB' AND table='$SHIP_STAGE' ORDER BY position FORMAT TSVRaw" \
    | awk 'BEGIN{s=""} {printf "%s`%s`",s,$0; s=", "} END{print ""}'
}

create_shipments_stage() {
  log "Creating $CH_DB.$SHIP_STAGE from the embedded ClickHouse schema."
  ch --multiquery <<SQL
DROP TABLE IF EXISTS $CH_DB.$SHIP_STAGE SYNC;
CREATE TABLE $CH_DB.$SHIP_STAGE
(
    id Int64,
    quarter LowCardinality(Nullable(String)),
    week_of_year Nullable(Int32),
    mtons Nullable(Decimal(38, 10)),
    teus Nullable(Decimal(38, 10)),
    is_containerized Nullable(Bool),
    is_hazmat Nullable(Bool),
    hs_code_2_desc LowCardinality(Nullable(String)),
    hs_code_2_digit Nullable(Int32),
    hs_code_4_digit Nullable(Int32),
    hs_code_8_desc LowCardinality(Nullable(String)),
    hs_code_8_digit Nullable(Int32),
    lcl_flag LowCardinality(Nullable(String)),
    is_reefer Nullable(Bool),
    is_roro Nullable(Bool),
    estimated_us_value_fob Nullable(Decimal(38, 10)),
    total_us_import_value Nullable(Decimal(38, 10)),
    vessel_name LowCardinality(Nullable(String)),
    method_of_transportation LowCardinality(Nullable(String)),
    foreign_company_address Nullable(String),
    foreign_company_address_line_2 Nullable(String),
    foreign_company_address_line_3 Nullable(String),
    foreign_company_address_line_4 Nullable(String),
    domestic_company_name Nullable(String),
    domestic_company_address_line_2 Nullable(String),
    foreign_company_name Nullable(String),
    domestic_company_city LowCardinality(Nullable(String)),
    domestic_address Nullable(String),
    domestic_pin LowCardinality(Nullable(String)),
    customs_house_agent LowCardinality(Nullable(String)),
    ultimate_territory LowCardinality(Nullable(String)),
    ultimate_port_code LowCardinality(Nullable(String)),
    ultimate_region LowCardinality(Nullable(String)),
    us_coast LowCardinality(Nullable(String)),
    us_port LowCardinality(Nullable(String)),
    us_company_address Nullable(String),
    us_company_city LowCardinality(Nullable(String)),
    us_company_duns Nullable(String),
    us_company Nullable(String),
    us_company_sales_territory LowCardinality(Nullable(String)),
    foreign_company_city LowCardinality(Nullable(String)),
    foreign_company Nullable(String),
    notify_company Nullable(String),
    notify_company_state LowCardinality(Nullable(String)),
    oti_domestic LowCardinality(Nullable(String)),
    reporter_province LowCardinality(Nullable(String)),
    incoterm1 LowCardinality(Nullable(String)),
    domestic_address_vn Nullable(String),
    domestic_company_phone Nullable(String),
    nvocc_line LowCardinality(Nullable(String)),
    nvocc_name_oti LowCardinality(Nullable(String)),
    oti_method LowCardinality(Nullable(String)),
    oti_name LowCardinality(Nullable(String)),
    scac LowCardinality(Nullable(String)),
    ship_type_level_2 LowCardinality(Nullable(String)),
    date Nullable(Date32),
    month Nullable(Int32),
    teus_estimated Nullable(Decimal(38, 10)),
    trade_direction LowCardinality(Nullable(String)),
    domestic_company_address_line_1 Nullable(String),
    shipping_forwarder LowCardinality(Nullable(String)),
    us_company_state LowCardinality(Nullable(String)),
    bol_number Nullable(String),
    bol_id Nullable(String),
    master_bol_number Nullable(String),
    us_company_teu_volume Nullable(Decimal(38, 10)),
    purpose LowCardinality(Nullable(String)),
    domestic_company_name_cleaned LowCardinality(Nullable(String)),
    foreign_company_name_cleaned LowCardinality(Nullable(String)),
    forwarder_name_cleaned LowCardinality(Nullable(String)),
    forwarders_sales_person_cleaned LowCardinality(Nullable(String)),
    domestic_company_city_cleaned LowCardinality(Nullable(String)),
    domestic_city_pincode_cleaned LowCardinality(Nullable(String)),
    foreign_company_city_cleaned LowCardinality(Nullable(String)),
    foreign_city_pincode_cleaned LowCardinality(Nullable(String)),
    cha_name_cleaned LowCardinality(Nullable(String)),
    commodity_group_cleaned LowCardinality(Nullable(String)),
    customer_rank_cleaned Nullable(Int32),
    trade_value_annual_usd_cleaned Nullable(Decimal(38, 10)),
    incoterms_cleaned LowCardinality(Nullable(String)),
    tradelane_name_cleaned LowCardinality(Nullable(String)),
    assigned_sp_cleaned LowCardinality(Nullable(String)),
    reporter_port_cleaned LowCardinality(Nullable(String)),
    partner_port_cleaned LowCardinality(Nullable(String)),
    reporter_country_cleaned LowCardinality(Nullable(String)),
    partner_country_cleaned LowCardinality(Nullable(String)),
    foreign_company_address_line_1 Nullable(String),
    container_size LowCardinality(Nullable(String)),
    ship_line_name LowCardinality(Nullable(String)),
    is_target Nullable(Bool),
    is_mgh_presence Nullable(Bool),
    is_20_80_domestic_company Nullable(Bool),
    is_20_80_foreign_company Nullable(Bool),
    INDEX idx_domestic_company_name domestic_company_name_cleaned TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_foreign_company_name foreign_company_name_cleaned TYPE bloom_filter(0.01) GRANULARITY 4,
    INDEX idx_cha_name cha_name_cleaned TYPE bloom_filter(0.01) GRANULARITY 4
)
ENGINE = MergeTree
PARTITION BY intDiv(id - 1, 2000000)
ORDER BY
(
    ifNull(reporter_country_cleaned, ''),
    ifNull(trade_direction, ''),
    ifNull(method_of_transportation, ''),
    ifNull(commodity_group_cleaned, ''),
    ifNull(is_target, false),
    ifNull(domestic_company_city_cleaned, ''),
    ifNull(is_20_80_domestic_company, false),
    ifNull(reporter_port_cleaned, ''),
    ifNull(partner_country_cleaned, ''),
    ifNull(partner_port_cleaned, ''),
    ifNull(tradelane_name_cleaned, ''),
    ifNull(hs_code_2_digit, 0),
    ifNull(is_mgh_presence, false),
    ifNull(date, toDate32('1970-01-01')),
    id
)
SETTINGS index_granularity = 8192;
SQL
}

validate_created_stage_schema() {
  local pg_file ch_file expected_lc_file actual_lc_file report_file
  pg_file="$STATE_DIR/stage_check_pg.tsv"
  ch_file="$STATE_DIR/stage_check_ch.tsv"
  expected_lc_file="$STATE_DIR/stage_check_expected_lc.txt"
  actual_lc_file="$STATE_DIR/stage_check_actual_lc.txt"
  report_file="$STATE_DIR/stage_schema_errors.txt"

  psql_run -At -F $'\t' -c "
SELECT column_name,data_type,is_nullable
FROM information_schema.columns
WHERE table_schema='$PG_SCHEMA' AND table_name='$PG_TABLE'
ORDER BY ordinal_position" > "$pg_file"

  ch --query "
SELECT name,type
FROM system.columns
WHERE database='$CH_DB' AND table='$SHIP_STAGE'
ORDER BY position
FORMAT TSVRaw" > "$ch_file"

  expected_low_cardinality_columns > "$expected_lc_file"
  ch --query "
SELECT name
FROM system.columns
WHERE database='$CH_DB' AND table='$SHIP_STAGE'
  AND startsWith(type,'LowCardinality(')
ORDER BY position
FORMAT TSVRaw" > "$actual_lc_file"

  set +e
  "$PYTHON_BIN" - "$pg_file" "$ch_file" > "$report_file" <<'PY'
import sys

pg_path, ch_path = sys.argv[1:3]
pg_rows = [line.rstrip("\n").split("\t") for line in open(pg_path, encoding="utf-8")]
ch_rows = [line.rstrip("\n").split("\t") for line in open(ch_path, encoding="utf-8")]

base_mapping = {
    "bigint": "Int64",
    "integer": "Int32",
    "smallint": "Int16",
    "numeric": "Decimal",
    "decimal": "Decimal",
    "boolean": "Bool",
    "date": "Date32",
    "timestamp without time zone": "DateTime64",
    "timestamp with time zone": "DateTime64",
    "text": "String",
    "character varying": "String",
    "character": "String",
}

def unwrap(ch_type):
    low_cardinality = False
    nullable = False
    value = ch_type
    if value.startswith("LowCardinality(") and value.endswith(")"):
        low_cardinality = True
        value = value[len("LowCardinality("):-1]
    if value.startswith("Nullable(") and value.endswith(")"):
        nullable = True
        value = value[len("Nullable("):-1]
    return value, nullable, low_cardinality

errors = []
if len(pg_rows) != len(ch_rows):
    errors.append(f"column count: PostgreSQL={len(pg_rows)}, ClickHouse={len(ch_rows)}")

for position, (pg, ch) in enumerate(zip(pg_rows, ch_rows), start=1):
    pg_name, pg_type, pg_nullable = pg
    ch_name, ch_type = ch
    if pg_name != ch_name:
        errors.append(f"position {position}: PostgreSQL column {pg_name!r}, ClickHouse column {ch_name!r}")
        continue
    expected_base = base_mapping.get(pg_type)
    if expected_base is None:
        errors.append(f"{pg_name}: unsupported PostgreSQL datatype {pg_type!r}")
        continue
    actual_base, actual_nullable, _ = unwrap(ch_type)
    base_ok = actual_base.startswith("Decimal(") if expected_base == "Decimal" else actual_base.startswith("DateTime64(") if expected_base == "DateTime64" else actual_base == expected_base
    expected_nullable = pg_nullable == "YES"
    if not base_ok or actual_nullable != expected_nullable:
        expected = f"{'Nullable(' if expected_nullable else ''}{expected_base}{')' if expected_nullable else ''}"
        errors.append(f"{pg_name}: PostgreSQL={pg_type} nullable={pg_nullable}; ClickHouse={ch_type}; expected base/nullability={expected}")

if errors:
    print("ERROR: incompatible PostgreSQL and ClickHouse schemas")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
PY
  local mapping_rc=$?
  set -e

  local lc_rc=0
  if ! cmp -s "$expected_lc_file" "$actual_lc_file"; then
    {
      echo 'ERROR: LowCardinality columns differ from the explicit script contract:'
      diff -u "$expected_lc_file" "$actual_lc_file" || true
    } >> "$report_file"
    lc_rc=1
  fi

  if (( mapping_rc != 0 || lc_rc != 0 )); then
    cat "$report_file" | tee -a "$LOG_FILE"
    ch --query "DROP TABLE IF EXISTS $CH_DB.$SHIP_STAGE SYNC"
    rm -f "$pg_file" "$ch_file" "$expected_lc_file" "$actual_lc_file" "$report_file"
    log 'No data was transferred or published. Update both embedded schema definitions before proceeding.'
    exit 2
  fi

  rm -f "$pg_file" "$ch_file" "$expected_lc_file" "$actual_lc_file" "$report_file"
  log "Created-stage schema check OK: $EXPECTED_COLUMN_COUNT compatible datatypes and 50 explicit LowCardinality columns."
}

preflight() {
  log "Preflight: PostgreSQL public.$PG_TABLE"
  local pg_exists
  pg_exists="$(psql_run -Atqc "SELECT to_regclass('$PG_SCHEMA.$PG_TABLE') IS NOT NULL")"
  [[ "$pg_exists" == 't' ]] || { log "ERROR: PostgreSQL $PG_SCHEMA.$PG_TABLE does not exist."; exit 2; }

  log "Preflight: ClickHouse connection and embedded $EXPECTED_COLUMN_COUNT-column schema contract"
  ch --query "SELECT version() AS version, currentDatabase() AS current_database"

  local pg_cols actual_schema_file expected_schema_file
  pg_cols="$(psql_run -Atqc "SELECT count(*) FROM information_schema.columns WHERE table_schema='$PG_SCHEMA' AND table_name='$PG_TABLE'")"
  [[ "$pg_cols" == "$EXPECTED_COLUMN_COUNT" ]] || {
    log "ERROR: PostgreSQL has $pg_cols columns; embedded contract expects $EXPECTED_COLUMN_COUNT."
    log 'Update the embedded PostgreSQL and ClickHouse schema definitions before proceeding.'
    exit 2
  }

  actual_schema_file="$STATE_DIR/actual_pg_schema.tmp"
  expected_schema_file="$STATE_DIR/expected_pg_schema.tmp"
  psql_run -At -F $'\t' -c "SELECT column_name,data_type,udt_name FROM information_schema.columns WHERE table_schema='$PG_SCHEMA' AND table_name='$PG_TABLE' ORDER BY ordinal_position" > "$actual_schema_file"
  expected_pg_schema > "$expected_schema_file"
  if ! cmp -s "$actual_schema_file" "$expected_schema_file"; then
    log 'ERROR: PostgreSQL names, datatypes, or column order differ from the embedded schema contract:'
    diff -u "$expected_schema_file" "$actual_schema_file" || true
    rm -f "$actual_schema_file" "$expected_schema_file"
    log 'Update the embedded PostgreSQL and ClickHouse schema definitions before proceeding.'
    exit 2
  fi
  rm -f "$actual_schema_file" "$expected_schema_file"

  log "Preflight OK: all $pg_cols PostgreSQL columns, datatypes, and positions match the embedded contract."
  ch --query "SELECT count() FROM (SELECT \"id\" FROM $(postgresql_source) LIMIT 1)" >/dev/null
}

start_new_run() {
  RUN_ID="$(date '+%Y%m%d_%H%M%S')"
  SHIP_STAGE="${CH_SHIPMENTS}__stage_${RUN_ID}"
  FILTER_STAGE="${CH_FILTERS}__stage_${RUN_ID}"
  OLD_SHIPMENTS="${CH_SHIPMENTS}__old_${RUN_ID}"
  OLD_FILTERS="${CH_FILTERS}__old_${RUN_ID}"
  log 'Calculating exact PostgreSQL source row count for final validation.'
  read -r MIN_ID MAX_ID EXPECTED_ROWS < <(psql_run -Atqc "
SET max_parallel_workers_per_gather=8;
SELECT COALESCE(min(id),0) || ' ' || COALESCE(max(id),0) || ' ' || count(*)
FROM $PG_SCHEMA.$PG_TABLE;")
  NEXT_ID="$MIN_ID"
  STATUS='loading_shipments'

  create_shipments_stage
  validate_created_stage_schema
  save_state
}

discard_saved_run_if_requested() {
  [[ "${FORCE_FRESH:-0}" == '1' ]] || return 0
  [[ -f "$STATE_FILE" ]] || { log 'FORCE_FRESH=1: no saved run exists; starting fresh.'; return 0; }

  # shellcheck disable=SC1090
  source "$STATE_FILE"
  [[ "$SHIP_STAGE" =~ ^shipments_${YEAR}__stage_[0-9_]+$ ]] || { log 'ERROR: unsafe saved shipment staging name.'; exit 2; }
  [[ "$FILTER_STAGE" =~ ^filter_options_${YEAR}__stage_[0-9_]+$ ]] || { log 'ERROR: unsafe saved filter staging name.'; exit 2; }

  log "FORCE_FRESH=1: discarding saved run $RUN_ID and its staging tables. Published tables are untouched."
  ch --multiquery --query "
DROP TABLE IF EXISTS $CH_DB.$SHIP_STAGE SYNC;
DROP TABLE IF EXISTS $CH_DB.$FILTER_STAGE SYNC;"
  mv "$STATE_FILE" "$STATE_DIR/state_${RUN_ID}_forced_fresh.env"
  rm -f "$FILTER_STATUS_FILE" "$FILTER_STATUS_FILE.tmp"
}

load_or_initialize() {
  if [[ -f "$STATE_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE"
    [[ "$YEAR" == "${YEAR:-}" ]] || { log 'ERROR: state year mismatch.'; exit 2; }
    [[ -n "${EXPECTED_ROWS:-}" ]] || { log 'ERROR: saved state predates exact row validation; remove this state directory and start a fresh refresh.'; exit 2; }
    if [[ "$STATUS" != 'done' ]]; then
      log "Resuming year $YEAR: RUN_ID=$RUN_ID STATUS=$STATUS NEXT_ID=$NEXT_ID"
      log "Resume keeps the existing staging schema. The 50-column LowCardinality contract applies to new runs only."
      return
    fi
    log "Previous refresh is complete; starting a fresh run."
    mv "$STATE_FILE" "$STATE_DIR/state_${RUN_ID}_done.env"
  fi
  start_new_run
}

print_progress() {
  local rows pct
  rows="$(ch --query "SELECT count() FROM $CH_DB.$SHIP_STAGE" 2>/dev/null || echo unknown)"
  pct="$(awk -v n="$NEXT_ID" -v min="$MIN_ID" -v max="$MAX_ID" 'BEGIN {d=max-min+1; printf "%.2f%%", (d>0 ? (n-min)*100/d : 100)}')"
  log "Shipment progress: $pct | next_id=$NEXT_ID | max_id=$MAX_ID | stage_rows=$rows"
}

insert_range() {
  local start="$1" end="$2" partition_id="$3" columns="$4"
  ch --query "ALTER TABLE $CH_DB.$SHIP_STAGE DROP PARTITION $partition_id" >/dev/null 2>&1 || true
  ch --query "
INSERT INTO $CH_DB.$SHIP_STAGE ($columns)
SELECT $columns
FROM $(postgresql_source)
WHERE \"id\" >= $start AND \"id\" < $end
SETTINGS max_threads=$CH_MAX_THREADS, max_insert_threads=$CH_MAX_INSERT_THREADS;"
}

reconcile_shipment_group() {
  local start="$1" end="$2" pg_rows ch_rows ch_unique
  pg_rows="$(psql_run -Atqc "SELECT count(*) FROM $PG_SCHEMA.$PG_TABLE WHERE id >= $start AND id < $end;")"
  read -r ch_rows ch_unique < <(ch --format TSVRaw --query "
SELECT count(), uniqExact(id)
FROM $CH_DB.$SHIP_STAGE
WHERE id >= $start AND id < $end")

  if [[ "$ch_rows" == "$pg_rows" && "$ch_unique" == "$pg_rows" ]]; then
    log "Reconciled committed shipment range [$start,$end): rows=$ch_rows unique_ids=$ch_unique"
    return 0
  fi
  log "Shipment range [$start,$end) is incomplete: postgres_rows=$pg_rows stage_rows=$ch_rows unique_ids=$ch_unique"
  return 1
}

load_shipments() {
  [[ "$STATUS" == 'loading_shipments' ]] || return 0
  if (( MIN_ID == 0 && MAX_ID == 0 )); then
    STATUS='shipments_loaded'; save_state; return
  fi

  local columns start end partition group_end slots pid failures resume_end
  local pids=()
  columns="$(column_list)"

  # A client can lose its TCP connection after ClickHouse has committed an insert.
  # Reconcile the next whole worker group before retrying it to avoid needless reloads.
  resume_end=$(( NEXT_ID + INSERT_JOBS * BATCH_SIZE ))
  (( resume_end > MAX_ID + 1 )) && resume_end=$(( MAX_ID + 1 ))
  if (( NEXT_ID < resume_end )) && reconcile_shipment_group "$NEXT_ID" "$resume_end"; then
    NEXT_ID="$resume_end"
    save_state
  fi

  while (( NEXT_ID <= MAX_ID )); do
    pids=(); slots=0; start="$NEXT_ID"; group_end="$NEXT_ID"
    while (( slots < INSERT_JOBS && start <= MAX_ID )); do
      partition=$(( (start - 1) / BATCH_SIZE ))
      end=$(( (partition + 1) * BATCH_SIZE + 1 ))
      log "Launching shipment partition $partition, ids [$start,$end)"
      insert_range "$start" "$end" "$partition" "$columns" > "$STATE_DIR/ship_${start}_${end}.log" 2>&1 &
      pids+=("$!"); start="$end"; group_end="$end"; slots=$((slots + 1))
    done
    RUNNING_PIDS=("${pids[@]}")
    while true; do
      active=0
      for pid in "${pids[@]}"; do kill -0 "$pid" 2>/dev/null && active=$((active + 1)); done
      print_progress
      (( active == 0 )) && break
      sleep 30
    done
    failures=0
    for pid in "${pids[@]}"; do wait "$pid" || failures=$((failures + 1)); done
    RUNNING_PIDS=()
    if (( failures > 0 )); then
      log "WARNING: $failures shipment workers reported failure; reconciling the full group before retry."
      if ! reconcile_shipment_group "$NEXT_ID" "$group_end"; then
        log 'ERROR: shipment group is incomplete. State was not advanced; re-run to safely reload it.'
        exit 1
      fi
      log 'All rows committed despite the worker error; advancing the checkpoint.'
    fi
    NEXT_ID="$group_end"; save_state
  done
  STATUS='shipments_loaded'; save_state
  log "Shipment staging load complete: $(ch --query "SELECT count() FROM $CH_DB.$SHIP_STAGE") rows"
}

optimize_shipments() {
  [[ "$STATUS" == 'shipments_loaded' ]] || return 0
  local max_parts_per_partition
  max_parts_per_partition="$(ch --query "
SELECT coalesce(max(parts),0)
FROM (
  SELECT partition_id,count() AS parts
  FROM system.parts
  WHERE active AND database='$CH_DB' AND table='$SHIP_STAGE'
  GROUP BY partition_id
)")"
  if [[ "$RUN_SHIPMENT_OPTIMIZE" == '1' || ( "$RUN_SHIPMENT_OPTIMIZE" == 'smart' && "$max_parts_per_partition" -gt 8 ) ]]; then
    log "Optimizing staged shipments because max active parts per partition=$max_parts_per_partition."
    ch --query "OPTIMIZE TABLE $CH_DB.$SHIP_STAGE FINAL"
  else
    log "Skipping shipment OPTIMIZE FINAL; max active parts per partition=$max_parts_per_partition."
  fi
  STATUS='building_filters'; save_state
}

initialize_filters() {
  [[ "$STATUS" == 'building_filters' ]] || return 0
  if [[ ! -f "$FILTER_STATUS_FILE" || "$(exists_ch "$FILTER_STAGE")" != '1' ]]; then
    log "Creating staged filter-options table $CH_DB.$FILTER_STAGE"
    ch --multiquery <<SQL
DROP TABLE IF EXISTS $CH_DB.$FILTER_STAGE SYNC;
CREATE TABLE $CH_DB.$FILTER_STAGE
(
  col LowCardinality(String),
  value String,
  cnt UInt64
)
ENGINE = MergeTree
ORDER BY (col, value);
SQL
    printf 'col,status\n' > "$FILTER_STATUS_FILE"
    ch --query "SELECT name FROM system.columns WHERE database='$CH_DB' AND table='$SHIP_STAGE' AND startsWith(type,'LowCardinality(') ORDER BY position FORMAT TSVRaw" \
      | while IFS= read -r col; do [[ -n "$col" ]] && printf '%s,pending\n' "$col" >> "$FILTER_STATUS_FILE"; done
  fi
}

set_filter_status() {
  local col="$1" status="$2" temp="$FILTER_STATUS_FILE.tmp"
  awk -F, -v OFS=, -v c="$col" -v s="$status" 'NR==1{print;next} $1==c{$2=s}{print}' "$FILTER_STATUS_FILE" > "$temp"
  mv "$temp" "$FILTER_STATUS_FILE"
}

insert_filter_column() {
  local col="$1"
  ch --query "
INSERT INTO $CH_DB.$FILTER_STAGE (col,value,cnt)
SELECT '$col', toString(\`$col\`), count()
FROM $CH_DB.$SHIP_STAGE
WHERE \`$col\` IS NOT NULL
GROUP BY \`$col\`;"
}

finish_filter_group() {
  local i pid col failures=0
  for i in "${!FILTER_PIDS[@]}"; do
    pid="${FILTER_PIDS[$i]}"
    col="${FILTER_COLS[$i]}"
    if wait "$pid"; then
      set_filter_status "$col" done
      FILTER_COMPLETED=$((FILTER_COMPLETED + 1))
      log "Filter [$FILTER_COMPLETED/$FILTER_TOTAL] DONE: $col"
    else
      set_filter_status "$col" pending
      failures=$((failures + 1))
      log "ERROR: filter worker failed for $col; see $STATE_DIR/filter_${col}.log"
    fi
  done
  FILTER_PIDS=()
  FILTER_COLS=()
  RUNNING_PIDS=()
  (( failures == 0 ))
}

build_filters() {
  [[ "$STATUS" == 'building_filters' ]] || return 0
  initialize_filters
  local col status temp slots=0
  temp="$FILTER_STATUS_FILE.tmp"
  awk -F, -v OFS=, 'NR==1{print;next} $2=="in_progress"{$2="pending"}{print}' "$FILTER_STATUS_FILE" > "$temp"
  mv "$temp" "$FILTER_STATUS_FILE"
  FILTER_TOTAL="$(awk -F, 'NR>1{n++} END{print n+0}' "$FILTER_STATUS_FILE")"
  FILTER_COMPLETED="$(awk -F, 'NR>1 && $2=="done"{n++} END{print n+0}' "$FILTER_STATUS_FILE")"
  while IFS=, read -r col status; do
    [[ "$col" == 'col' || "$status" == 'done' ]] && continue
    set_filter_status "$col" in_progress
    log "Launching filter [$((FILTER_COMPLETED + slots + 1))/$FILTER_TOTAL]: $col"
    ch --query "
ALTER TABLE $CH_DB.$FILTER_STAGE DELETE WHERE col='$col' SETTINGS mutations_sync=2;
" >/dev/null
    insert_filter_column "$col" > "$STATE_DIR/filter_${col}.log" 2>&1 &
    FILTER_PIDS+=("$!")
    FILTER_COLS+=("$col")
    RUNNING_PIDS=("${FILTER_PIDS[@]}")
    slots=$((slots + 1))
    if (( slots == FILTER_JOBS )); then
      finish_filter_group || { log 'One or more filter workers failed. Re-run to resume.'; exit 1; }
      slots=0
    fi
  done < "$FILTER_STATUS_FILE"
  if (( slots > 0 )); then
    finish_filter_group || { log 'One or more filter workers failed. Re-run to resume.'; exit 1; }
  fi
  STATUS='filters_built'; save_state
}

validate_staging() {
  [[ "$STATUS" == 'filters_built' ]] || return 0
  local ship_rows ship_min_id ship_max_id filter_rows filter_cols expected_filter_cols populated_filter_cols duplicate_options completed_filter_status
  local col sep='' populated_expression=''
  ship_rows="$(ch --query "SELECT count() FROM $CH_DB.$SHIP_STAGE")"
  read -r ship_min_id ship_max_id < <(ch --query "SELECT coalesce(min(id),0),coalesce(max(id),0) FROM $CH_DB.$SHIP_STAGE FORMAT TSVRaw")
  filter_rows="$(ch --query "SELECT count() FROM $CH_DB.$FILTER_STAGE")"
  filter_cols="$(ch --query "SELECT uniqExact(col) FROM $CH_DB.$FILTER_STAGE")"
  expected_filter_cols="$(ch --query "SELECT count() FROM system.columns WHERE database='$CH_DB' AND table='$SHIP_STAGE' AND startsWith(type,'LowCardinality(')")"
  completed_filter_status="$(awk -F, 'NR>1 && $2=="done"{n++} END{print n+0}' "$FILTER_STATUS_FILE")"
  while IFS= read -r col; do
    [[ -n "$col" ]] || continue
    populated_expression+="${sep}toUInt64(countIf(\`$col\` IS NOT NULL) > 0)"
    sep=' + '
  # Match the existing stage on resume, including runs created with the older schema.
  done < <(ch --query "SELECT name FROM system.columns WHERE database='$CH_DB' AND table='$SHIP_STAGE' AND startsWith(type,'LowCardinality(') ORDER BY position FORMAT TSVRaw")
  populated_filter_cols="$(ch --query "SELECT $populated_expression FROM $CH_DB.$SHIP_STAGE")"
  duplicate_options="$(ch --query "SELECT count() - uniqExact(tuple(col,value)) FROM $CH_DB.$FILTER_STAGE")"
  [[ "$ship_rows" == "$EXPECTED_ROWS" ]] || { log "ERROR: staged shipment rows=$ship_rows; exact PostgreSQL source rows=$EXPECTED_ROWS"; exit 2; }
  [[ "$ship_min_id" == "$MIN_ID" && "$ship_max_id" == "$MAX_ID" ]] || { log "ERROR: staged id range=[$ship_min_id,$ship_max_id], source id range=[$MIN_ID,$MAX_ID]"; exit 2; }
  [[ "$completed_filter_status" == "$expected_filter_cols" ]] || { log "ERROR: completed filter status count $completed_filter_status != expected schema columns $expected_filter_cols"; exit 2; }
  [[ "$filter_cols" == "$populated_filter_cols" ]] || { log "ERROR: generated filter column count $filter_cols != populated LowCardinality columns $populated_filter_cols"; exit 2; }
  [[ "$duplicate_options" == '0' ]] || { log "ERROR: filter table contains $duplicate_options duplicate (col,value) rows"; exit 2; }
  log "Validation OK: exact_rows=$ship_rows id_range=[$ship_min_id,$ship_max_id] filter_schema_columns=$expected_filter_cols populated_filter_columns=$filter_cols filter_rows=$filter_rows duplicates=0"
  if [[ "$RUN_FILTER_OPTIMIZE" == '1' ]]; then
    log 'Optimizing staged filter options.'
    ch --query "OPTIMIZE TABLE $CH_DB.$FILTER_STAGE FINAL"
  fi
  STATUS='ready_to_publish'; save_state
}

publish() {
  [[ "$STATUS" == 'ready_to_publish' || "$STATUS" == 'publishing' ]] || return 0
  STATUS='publishing'; save_state

  local ship_stage_exists filter_stage_exists
  ship_stage_exists="$(exists_ch "$SHIP_STAGE")"
  filter_stage_exists="$(exists_ch "$FILTER_STAGE")"
  if [[ "$ship_stage_exists" == '0' && "$filter_stage_exists" == '0' && \
        "$(exists_ch "$CH_SHIPMENTS")" == '1' && "$(exists_ch "$CH_FILTERS")" == '1' ]]; then
    log 'Publish was already completed; finishing cleanup.'
  else
    [[ "$ship_stage_exists" == '1' && "$filter_stage_exists" == '1' ]] || { log 'ERROR: incomplete staging tables during publish.'; exit 2; }
    local pairs=''
    if [[ "$(exists_ch "$CH_SHIPMENTS")" == '1' ]]; then pairs+="$CH_DB.$CH_SHIPMENTS TO $CH_DB.$OLD_SHIPMENTS, "; fi
    if [[ "$(exists_ch "$CH_FILTERS")" == '1' ]]; then pairs+="$CH_DB.$CH_FILTERS TO $CH_DB.$OLD_FILTERS, "; fi
    pairs+="$CH_DB.$SHIP_STAGE TO $CH_DB.$CH_SHIPMENTS, $CH_DB.$FILTER_STAGE TO $CH_DB.$CH_FILTERS"
    log "Publishing $CH_SHIPMENTS and $CH_FILTERS together."
    ch --query "RENAME TABLE $pairs"
  fi

  ch --multiquery <<SQL
DROP TABLE IF EXISTS $CH_DB.$OLD_SHIPMENTS SYNC;
DROP TABLE IF EXISTS $CH_DB.$OLD_FILTERS SYNC;
SQL
  STATUS='done'; save_state
}

summary() {
  log "Final tables:"
  ch --query "
SELECT name, engine, total_rows, formatReadableSize(total_bytes) AS size
FROM system.tables
WHERE database='$CH_DB' AND name IN ('$CH_SHIPMENTS','$CH_FILTERS')
ORDER BY name FORMAT PrettyCompact"
  log "Schema source: embedded contract in $0"
  log "State: $STATE_FILE"
  log 'Done.'
}

main() {
  log "Refresh requested for year $YEAR"
  log "PostgreSQL: $PG_SCHEMA.$PG_TABLE"
  log "ClickHouse outputs: $CH_DB.$CH_SHIPMENTS and $CH_DB.$CH_FILTERS"
  log "Schema source of truth: embedded PostgreSQL contract and ClickHouse CREATE TABLE definition"
  log "Performance: batch_size=$BATCH_SIZE shipment_jobs=$INSERT_JOBS filter_jobs=$FILTER_JOBS threads_per_job=$CH_MAX_THREADS"
  log "Safety: resumable partitions, exact source row count, id-range validation, filter duplicate validation, staged publish"
  preflight
  if [[ "${PREFLIGHT_ONLY:-0}" == '1' ]]; then
    log 'PREFLIGHT_ONLY=1: verification complete; no tables or data were changed.'
    exit 0
  fi
  discard_saved_run_if_requested
  load_or_initialize
  load_shipments
  optimize_shipments
  build_filters
  validate_staging
  publish
  summary
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main
fi
