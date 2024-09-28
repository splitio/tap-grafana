"""
Tap configuration related stuff
"""
from voluptuous import Schema, Required, Optional

CONFIG_CONTRACT = Schema([{
    Required('table_name'): str,
    Required('query'): str,
    Required('interval'): str,
    Optional('max_lookback_days'): int,
}])
