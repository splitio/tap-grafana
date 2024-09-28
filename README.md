# tap-sumologic

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
    "sumologic_access_id": "ACCESS_ID",
    "sumologic_access_key": "ACCESS_KEY",
    "sumologic_root_url": "https://api.us2.sumologic.com/api",
    "start_date": "2020-01-01T00:00:00",
    "end_date": "2020-01-05T00:00:00",
    "tables": [{
        "query": "_sourceCategory=prod/fastly/sdk | _timeslice 1d as day | count by day, api_key",
        "table_name": "my_table",
        "max_lookback_days": 10, 
        "time_property": ["day"] 
    }]
}
```

max_lookback_days: by default is 7 days. Number of days it queries Sumologic back from today. Sumologic doesn't perform well when going to far back so use with caution.
time_property: this is the field that has the time if any. It allows to track the last processed date. 