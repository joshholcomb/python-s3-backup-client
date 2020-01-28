# python-s3-backup-client
python-s3-backup-client is a python app to backup and restore files to/from an s3 bucket with optional client side encryption.  Backup mode will backup files from a local machine to a s3 target.  Restore mode will copy the data from s3 to a designated restore directory on the local machine.

## dependencies
* pyinstaller
* minio
* pyaescrypt
* configparser

## S3 Implementation
Uses Minio python API for S3 connectivity.

## encryption implementation
Uses PyAESCrypt to perform client side encryption on each file before uploading it to s3.  If the optional encryption is used, only the files on the s3 bucket will be encrypted.

## building executables
Build standalone executables from the python scripts for easy deployment to target machines which may not have a python environment.


| File                |Description            | Command  |
| :------------------- |:---------------------| :-------- |
|backup-client.py     |For a GUI based backup client executable|`pyinstaller --onefile --windowed backup-client.py`|
|backup.py|For a command line backup client|`pyinstaller --onefile backup.py`|
|restore.py|For a command line restore utility|`pyinstaller --onefile restore.py`|

## config
Site level configuration is performed in config/bkup.conf
