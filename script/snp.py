CREATE TABLE snp (
    id BIGSERIAL PRIMARY KEY,
    "Quantity"                        NUMERIC,
    "Unit of Measure"                 TEXT,
    "HS Code 2 Desc"                  TEXT,
    "HS Code 2 Digit"                 SMALLINT,
    "lcl_flag"                        TEXT,
    "Raw Commodity Desc"              TEXT,
    "is_reefer"                       BOOLEAN,
    "is_roro"                         BOOLEAN,
    "Estimated Commodity Weight"      NUMERIC,
    "Total US Import Value"           NUMERIC,
    "Month"                           SMALLINT,
    "Week Of Year"                    SMALLINT,
    "Year"                            INTEGER,
    "MTONs"                           NUMERIC,
    "TEUs (Estimated)"                NUMERIC,
    "Trade Direction"                 TEXT,
    "Containerized"                   BOOLEAN,
    "Reporter"                        TEXT,
    "Reporter Port"                   TEXT,
    "Partner"                         TEXT,
    "Partner Port"                    TEXT,
    "Foreign Address"                 TEXT,
    "Domestic Company"                TEXT,
    "Foreign Company"                 TEXT,
    "Domestic City"                   TEXT,
    "Domestic Code"                   TEXT,
    "Domestic Address"                TEXT,
    "Domestic Pin"                    TEXT,
    "Customs House Agent"             TEXT,
    "Customs House Agent Code"        TEXT,
    "Method of Transportation"        TEXT
);

\copy snp(
    "Quantity","Unit of Measure","HS Code 2 Desc","HS Code 2 Digit","lcl_flag",
    "Raw Commodity Desc","is_reefer","is_roro","Estimated Commodity Weight",
    "Total US Import Value","Month","Week Of Year","Year","MTONs","TEUs (Estimated)",
    "Trade Direction","Containerized","Reporter","Reporter Port","Partner",
    "Partner Port","Foreign Address","Domestic Company","Foreign Company",
    "Domestic City","Domestic Code","Domestic Address","Domestic Pin",
    "Customs House Agent","Customs House Agent Code","Method of Transportation"
)
FROM '/Users/atom/Downloads/snp_utf8.csv'
WITH (
    FORMAT csv,
    HEADER true,
    QUOTE '"',
    NULL '',
    FORCE_NULL (
        "Quantity","Estimated Commodity Weight",
        "Total US Import Value","MTONs","TEUs (Estimated)"
    )
);


SET statement_timeout = 0;
SET lock_timeout = 0;
SET maintenance_work_mem = '2GB';

CREATE INDEX IF NOT EXISTS idx_snp_hs2 ON snp ("HS Code 2 Digit");
CREATE INDEX IF NOT EXISTS idx_snp_year_month ON snp ("Year","Month");
CREATE INDEX IF NOT EXISTS idx_snp_week ON snp ("Week Of Year");
CREATE INDEX IF NOT EXISTS idx_snp_trade_dir ON snp ("Trade Direction");
CREATE INDEX IF NOT EXISTS idx_snp_container ON snp ("Containerized");

CREATE INDEX IF NOT EXISTS idx_snp_reporter_port ON snp ("Reporter Port");
CREATE INDEX IF NOT EXISTS idx_snp_partner_port ON snp ("Partner Port");
CREATE INDEX IF NOT EXISTS idx_snp_reporter ON snp ("Reporter");
CREATE INDEX IF NOT EXISTS idx_snp_partner ON snp ("Partner");

CREATE INDEX IF NOT EXISTS idx_snp_value ON snp ("Total US Import Value");
CREATE INDEX IF NOT EXISTS idx_snp_weight ON snp ("Estimated Commodity Weight");

CREATE INDEX IF NOT EXISTS idx_snp_hs_year_dir
ON snp ("HS Code 2 Digit","Year","Trade Direction");

CREATE INDEX IF NOT EXISTS idx_snp_commodity_gin
ON snp USING GIN (to_tsvector('english',"Raw Commodity Desc"));

CREATE INDEX IF NOT EXISTS idx_snp_year_brin ON snp USING BRIN ("Year");
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_snp_domestic_company ON snp ("Domestic Company");

VACUUM ANALYZE snp;

