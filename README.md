# Synology Active Backups for Business log parser

`synology_abfb_log_parser` parses the [Synology Active Backups for Business][1] logs on the agent allowing and provides a way to search the logs. The examples show how to send a TRMM alert for various log entries.

[1]: https://kb.synology.com/en-br/DSM/help/ActiveBackup/activebackup_business_activities?version=7

## Events

Events have the following structure. Given this log entry:
```text
Nov 25 22:12:34 [INFO] async-worker.cpp (56): Worker (0): get event '1: routine {"subaction": "heart_beat"}', start processing
```

The events returned will be like this:
```Python
events[0] = {
    "datetime": "datestamp.datestamp class",
    "timestamp": "Nov 25 22:12:34",
    "priority": "INFO",
    "method_name": "async-worker.cpp",
    "method_num": "56",
    "message": "Worker (0): get event '1: routine {\"subaction\": \"heart_beat\"}', start processing",
    "json": {
        "subaction": "heart_beat"
    },
}
```
