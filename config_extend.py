# base
from config import config_column_int_mapping as base_config_column_int_mapping
from config import config_postgres as base_config_postgres
from config import config_api as base_config_api

# atom
config_column_int_mapping = {
**base_config_column_int_mapping,
}

config_postgres = {
**base_config_postgres,
"table": {
**base_config_postgres["table"],
},
}

config_api = {
**base_config_api,
}

# misc
