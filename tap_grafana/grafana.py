"""
Modules containing all Grafana related features
"""
from typing import List, Dict

import backoff
import singer
import requests
from datetime import datetime, timezone
import time
from dateutil.relativedelta import *

import requests
from urllib.parse import urlencode
import json

LOGGER = singer.get_logger()
RECORD_FETCHING_LIMIT = 10000

def retry_pattern():
    """
    Retry decorator to retry failed functions
    :return:
    """
    return backoff.on_exception(backoff.expo,
                                requests.HTTPError,
                                max_tries=5,
                                on_backoff=log_backoff_attempt,
                                factor=10)


def log_backoff_attempt(details):
    """
    For logging attempts to connect with Amazon
    :param details:
    :return:
    """
    LOGGER.info("Error detected communicating with Grafana, triggering backoff: %d try", details.get("tries"))


@retry_pattern()
def get_schema_for_table(config: Dict, table_spec: Dict) -> Dict:
    """
    Detects json schema using a record set of query
    :param config: Tap config
    :param table_spec: tables specs
    :return: detected schema
    """
    schema = {}
    LOGGER.info('Getting records for query to determine table schema.')

    q = table_spec.get('query') 
    interval = table_spec.get('interval') 
    from_time = (datetime.now(timezone.utc) + relativedelta(minutes=-15)).strftime('%Y-%m-%dT%H:%M:%SZ')
    to_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    fields = get_grafana_fields(config, q, interval, from_time, to_time)

    key_properties = []
    for field in fields:
        field_name = field['name']
        field_type = field['fieldType']
        key_field = field['keyField']

        schema[field_name] = {
            'type': ['null', 'string']
        }

        if field_type == 'int':
            schema[field_name]['type'].append('integer')
        elif field_type == 'long':
            schema[field_name]['type'].append('integer')
        elif field_type == 'double':
            schema[field_name]['type'].append('number')
        elif field_type == 'boolean':
            schema[field_name]['type'].append('boolean')

        if key_field:
            key_properties.append(field_name)

    return {
        'type': 'object',
        'properties': schema,
        'key_properties': key_properties
    }

def get_grafana_fields(config, query, interval, from_time, to_time):
    fields = []
    params = {}
    params['query'] = query
    params['start'] = from_time
    if to_time:
        params['end'] = to_time

    LOGGER.info("Run query in grafana: " + query + "with params:" + str(params))
    response = request_to_grafana(config, "/loki/api/v1/query_range", params)
    if response:
        fields = []
        
        resultType = response['resultType']
        # add all dimensions
        dimensions = []
        if resultType == 'matrix':
            dimensions = response['result'][0]['metric']
        elif resultType == 'streams':
            dimensions = response['result'][0]['stream']
        else:
            raise Exception("Unknown resultType received from Grafana (only matrix and streams are supported): "+ resultType)
        # always have the time field for query_range
        fields.append({'name': 'time', 'fieldType': 'integer', 'keyField': True})
        
        for field in dimensions:
            fields.append({'name': field, 'fieldType': 'string', 'keyField': True})
            
        if resultType == 'matrix':
            fields.append({'name': 'value', 'fieldType': 'string', 'keyField': False})

    return fields

def get_grafana_records(config, query, interval, from_time, to_time):
    records = []
    
    now_datetime = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
    custom_columns = {
        '_SDC_EXTRACTED_AT': now_datetime,
        '_SDC_BATCHED_AT': now_datetime,
        '_SDC_DELETED_AT': None
    }
    
    params = {}
    params['query'] = query
    if interval:
        params['step'] = interval # for matrix
    else:
        params['limit'] = "50000" # for streams
    params['start'] = from_time
    if to_time:
        params['end'] = to_time

    LOGGER.info("Run query in grafana: " + query + " with params: " + str(params))
    response = request_to_grafana(config, "/loki/api/v1/query_range", params)
    count = 0
    if response:
        resultType = response['resultType']
        for rec in response['result']:
            record = {}
            
            # add all dimensions
            dimensions = []
            if resultType == 'matrix':
                dimensions = rec['metric']
            elif resultType == 'streams':
                dimensions = rec['stream']
            else:
                raise Exception("Unknown resultType received from Grafana (only matrix and streams are supported): "+ resultType)
                
            for dim in dimensions:
                record[dim] = dimensions[dim] or ''
            
            values = rec['values']
            for value in values:
                record['time'] = value[0]
                if resultType == 'matrix':
                    record['value'] = value[1] or ''
                # extract the result maps to put them in the list of records
                records.append({**record, **custom_columns})

                count = count + 1

    LOGGER.info("Got %d records.", count)
    return records


def request_to_grafana(config, urlpath, params):
    
    grafana_access_id = config['grafana_access_id']
    grafana_access_key = config['grafana_access_key']
    grafana_root_url = config['grafana_root_url']
    encodedparams = urlencode(params)
    
    full_url = grafana_root_url + "/" + urlpath + "?" + encodedparams
    LOGGER.info("full_url: %s", full_url)
    r = requests.get(full_url, auth=(grafana_access_id,grafana_access_key))
    
    if r.status_code == 200:
        response = json.loads(r.text)
        if response['status'] == 'success':
            return response['data']
    
    return None
            
