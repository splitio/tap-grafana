"""
Syncing related functions
"""

import sys
from typing import Dict, List
from singer import metadata, get_logger, Transformer, utils, get_bookmark, write_bookmark, write_state, write_record
from tap_grafana import grafana
from datetime import datetime, timezone
from dateutil.relativedelta import *
import pytz

utc=pytz.UTC

LOGGER = get_logger()


def sync_stream(config: Dict, state: Dict, table_spec: Dict, stream: Dict) -> int:
    """
    Sync the stream
    :param config: Connection and stream config
    :param state: current state
    :param table_spec: table specs
    :param stream: stream
    :return: count of streamed records
    """
    table_name = table_spec.get("table_name")
    modified_since_str = get_bookmark(state, table_name, 'modified_since') or config['start_date']
    end_date = config.get('end_date')
    interval = table_spec.get('interval')

    LOGGER.info('Config info - start_date: %s - end_date: %s - interval: %s', config['start_date'], end_date, interval)
    LOGGER.info('Syncing table "%s".', table_name)

    max_lookback_days = table_spec.get("max_lookback_days") or 7
    # we stop at 5 minutes ago because data may not all be there yet in Grafana
    # if we do real time we would have gaps of data for the data that comes in later.
    end_time = datetime.now(timezone.utc) + relativedelta(minutes=-5)
    if end_date:
        end_time = datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S')
    
    if interval == '1d':
        end_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
    elif interval == '1h':
        end_time = end_time.replace(minute=0, second=0, microsecond=0)
    
    modified_since = datetime.strptime(modified_since_str, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=utc)
    max_lookback_date = (end_time + relativedelta(days=-max_lookback_days))
    from_time = modified_since if modified_since > max_lookback_date else max_lookback_date
    
    if interval == '1d':
        from_time = from_time.replace(hour=0, minute=0, second=0, microsecond=0)
    elif interval == '1h':
        from_time = from_time.replace(minute=0, second=0, microsecond=0)
    
    end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    from_time_str = from_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    LOGGER.info('Getting records since %s to %s.', from_time_str, end_time_str)

    q = table_spec.get('query')
    records_streamed = 0

    LOGGER.info('Syncing query "%s" with interval %s from %s to %s, time.', q, interval, from_time_str, end_time_str)

    records = grafana.get_grafana_records(config, q, interval, from_time_str, end_time_str)

    records_synced = 0
    max_time = 0
    time_property = 'time'

    for record in records:
        # record biggest time property value to bookmark it
        if time_property:
            max_time = max(max_time, record[time_property])

        with Transformer() as transformer:
            to_write = transformer.transform(record, stream['schema'], metadata.to_map(stream['metadata']))

        write_record(table_name, to_write)
        records_synced += 1

    if time_property:
        end = datetime.fromtimestamp(int(max_time)/1000, timezone.utc)
        state = write_bookmark(state, table_name, 'modified_since', end.strftime('%Y-%m-%dT%H:%M:%S'))
        write_state(state)
        LOGGER.info('Wrote state with modified_since=%s', end.strftime('%Y-%m-%dT%H:%M:%S'))

    LOGGER.info('Wrote %s records for table "%s".', records_synced, table_name)

    return records_streamed

