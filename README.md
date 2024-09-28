# tap-grafana

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from [Sumologic](http://sumologic.com)
- Extracts the aggregated data based on a search query for a date range
- Outputs the schema for each resource
- Incrementally pulls data based on the input state

## Config

*config.json*
```json
{
    "grafana_access_id": "ACCESS_ID",
    "grafana_access_key": "ACCESS_KEY",
    "grafana_root_url": "https://logs-prod-006.grafana.net/",
    "start_date": "2020-01-01T00:00:00",
    "end_date": "2020-01-05T00:00:00",
    "tables": [{
        "query": "count_over_time({service_name=\"fastly\"}",
        "table_name": "my_table",
        "max_lookback_days": 10, 
        "interval": "1d"
    }]
}
```

max_lookback_days: by default is 7 days. Number of days it queries Grafana Loki back from today. 
interval: this is the granularity you want the data to be structured by. It currently supports "1d" (1 day) or "1h" (1 hour)
