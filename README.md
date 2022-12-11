# trmm-python

This repository contains various Python scripts for Tactical RMM.

## Synology Active Backups for Business Logs

`synology_activebackuplogs_snippet.py` is a TRMM snippet that parses the Synology Active Backup logs and allow you to
search them. The examples are a great place to start.

### Events

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
    "json_str": "{\"subaction\": \"heart_beat\"}",
    "json": {
        "subaction": "heart_beat"
    },
}
```

### Program

See the examples programs to search for log events.
