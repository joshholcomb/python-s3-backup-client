import getopt
import sys
import os
from datetime import datetime           # for date/time functions
import pyAesCrypt                       # for encrypting files
import configparser                     # for parsing the config file
from minio import Minio                 # minio library
from minio.error import ResponseError   # for minio exceptions
import timeit                           # for timing program runtime

import logging

import backup_util
from multiprocessing import Queue

# suppress ssl subjaltname warnings
import warnings
import urllib3
warnings.simplefilter('ignore', urllib3.exceptions.SecurityWarning)

# start timer
start = timeit.default_timer()

if not os.path.exists("./logs"):
    os.makedirs("./logs")

# setup a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = logging.FileHandler('./logs/restore.log')
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

logger.info("===== STARTING RESTORE RUN =====")

# load config
config = configparser.ConfigParser()
config.read('config/bkup.conf')
fileEncryptionPass = config['DEFAULT']['file.encryption_password']

# connect to minio
minioHost = config['MINIO']['minio.server']
minioAccess = config['MINIO']['minio.access_key']
minioSecret = config['MINIO']['minio.secret_key']
minioSslCert = config['MINIO']['minio.ssl_cacert']
minioBkt = config['MINIO']['minio.bucket_name']
os.environ['SSL_CERT_FILE'] = minioSslCert
logger.info("connecting to s3 server: [{}] - access_key: [{}] - secret: [{}]".format(minioHost, minioAccess, minioSecret))

minioClient = Minio(minioHost,
                access_key=minioAccess,
                secret_key=minioSecret,
                secure=True)


# get command line args passed
fullCmdArgs = sys.argv
argList = fullCmdArgs[1:]

# valid options
unixOptions = "r:f"
gnuOptions = ["restoreDir=", "folder="]

# parse the args passed 
argNum = len(argList)
logger.info("args passed: [{}] - parsing arguments".format(argNum))
try:
        arguments, values = getopt.getopt(argList, unixOptions, gnuOptions)
except getopt.error as err:
        # output the error - return with error code
        print(str(err))
        sys.exit(2)

restoreDir = ""
folder = ""

# print arguments
for currentArgument, currentValue in arguments:
    if currentArgument in ("-r", "--restoreDir"):
        logger.info(("input directory: [%s]") % (currentValue))
        restoreDir = currentValue
    elif currentArgument in ("-f", "--folder"):
        logger.info(("input directory: [%s]") % (currentValue))
        folder = currentValue


#
# end user input
#

q = Queue()
useQ = False
bucket = ""
backup_util.doRestore(restoreDir, folder, q, config, logger, useQ, bucket)


    