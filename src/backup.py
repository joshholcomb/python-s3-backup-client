import getopt
import sys
import os
from datetime import datetime           # for date/time functions
import configparser                     # for parsing the config file
import timeit                           # for timing program runtime
import logging                          # standard logging
import backup_util
from multiprocessing import Queue
from queue import Empty

import warnings
import urllib3

# suppress ssl subjaltname warnings
warnings.simplefilter('ignore', urllib3.exceptions.SecurityWarning)

if not os.path.exists("./logs"):
    os.makedirs("./logs")

# load config
config = configparser.ConfigParser()
config.read('config/bkup.conf')

# Multiprocess Queue - must be global
# note: not used for command line, but must exist
q = Queue()

# setup a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = logging.FileHandler('./logs/backup.log')
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

# start run
logger.info("===== STARTING BACKUP RUN =====")

# get command line args passed
fullCmdArgs = sys.argv
argList = fullCmdArgs[1:]

# valid options
unixOptions = "i:f:e"
gnuOptions = ["inputDir=", "folder=", "encrypt="]

# parse the args passed 
argNum = len(argList)
print("args passed: [{}] - parsing arguments".format(argNum))
try:
        arguments, values = getopt.getopt(argList, unixOptions, gnuOptions)
except getopt.error as err:
        # output the error - return with error code
        print(str(err))
        sys.exit(2)

inputDir = ""
folder = ""
encrypt = "false"

# print arguments
for currentArgument, currentValue in arguments:
        if currentArgument in ("-i", "--inputDir"):
                logger.info(("input directory: [%s]") % (currentValue))
                inputDir = currentValue
        elif currentArgument in ("-f", "--folder"):
                logger.info(("prefix: [%s]") % (currentValue))
                folder = currentValue
        elif currentArgument in ("-e", "--encrypt"):
                logger.info(("prefix: [%s]") % (currentValue))
                encrypt = currentValue

if (encrypt == "true"):
        encrypt = 1

# don't need the multiprocessing queue for command line
useQ = False
backup_util.doBackup(inputDir, folder, q, config, logger, useQ, encrypt)





