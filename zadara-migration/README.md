
# Parameters
The script takes in
```
rfsync.py 
--source _Specify the source folder to be migrated_
--destination _Specify the destination folder here to be migrated_
--rsync_flags _Specify flags for msrsync's rsync workers_
--logging_levels _Specify the logging level and monitor rfsync.log file, default is INFO_ [debug | info]
--mode  _sync_ | _remigrate_ | _generate_logs_
```

1. Use 'sync' mode with source, destination and rsync flags to run a normal rsync.
2. Use 'remigrate' mode with absolute path to 'FAILED_LOGS.csv' to run the script in re-migration mode 
3. Use 'generate-logs' mode  run the script to only generate a list of failed files from previous migration. This mode fails if 'logs' directory is empty or has been cleared.


## Script usage
 > sudo python2 rfsync.py --mode [sync | remigrate | generate_logs] --source {SOURCE_DIR} --destination {DESTINATION_DIR} --rsync_flags {RSYNC_FLAGS} --logging_level [debug | info]

The script generates 5 files to monitor various aspects of the migration,
1. rfsync.log - contains the flow of the script (logging at debug or info level)
2. msrsync_out.txt - contains the current status of msrsync - use this file to monitor migration's progress
3. msrsync_err.txt - contains the errors encountered by msrsync during migration and also path to log directory
4. FAILED_LOGS.csv - contains files which were failed during migration
5. timesheet.csv - contains the start time, end time and time taken for each migration to complete
6. {SCRIPT_DIR}/logs - folder that contains temp msrsync logs

##NOTE: 
1. Exclude directory feature not implemented - msrsync overrides this parameter
2. If new errors are identified add those errors to **errors_while_migration** array under the class **LogService**.


