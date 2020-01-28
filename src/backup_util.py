from datetime import datetime           # for date/time functions
import pyAesCrypt                       # for encrypting files
import configparser                     # for parsing the config file
from minio import Minio                 # s3 library
from minio.error import ResponseError   # for s3 exceptions
import timeit                           # for timing program runtime

import logging
import warnings
import urllib3
import os
import io
import sys

stopFlag = False

#
# utility function to set s3 folder name
#
def genS3Name(x):
    minioName = x

    # remove any leading slash
    if (x.startswith('\\')):
        minioName = minioName[1:]                   
    
    # use unix style slash
    minioName = minioName.replace("\\", "/")
    return minioName


#
# function to perform a backup job
#
def doBackup(inputDir, folder, q, config, logger, useQ, doEncrypt):
    # suppress s3 warnings
    warnings.simplefilter('ignore', urllib3.exceptions.SecurityWarning)

    # start timer
    start = timeit.default_timer()

    logger.info("===== STARTING BACKUP RUN =====")

    # config settings for file encryption
    fileEncryptionPass = config['DEFAULT']['file.encryption_password']
    encrypt = "false"

    # override config setting for encrypt with value passed in via doEncrypt
    if (doEncrypt == 1):
        encrypt = "true"
    else:
        encrypt = "false"

    # connect to s3
    s3Host = config['S3']['s3.server']
    s3Access = config['S3']['s3.access_key']
    s3Secret = config['S3']['s3.secret_key']
    s3SslCert = config['S3']['s3.ssl_cacert']
    s3Bkt = config['S3']['s3.bucket_name']
    os.environ['SSL_CERT_FILE'] = s3SslCert
    logger.info("connecting to s3 server: [{}] - access_key: [{}]".format(s3Host, s3Access))

    s3Client = Minio(s3Host,
                    access_key=s3Access,
                    secret_key=s3Secret,
                    secure=True)

    # make sure we have all of the input we need
    if (inputDir == "" or folder == ""):
        logger.error("missing mandatory input parameter - bailing out")
        return

    # make sure input directory exists
    if not os.path.exists(inputDir):
        logger.error("inputDir: [{}] - directory does not exist".format(inputDir))
        return


    #
    # clean out the target folder in s3
    #
    delete_start = timeit.default_timer()
    logger.info("deleting objects from s3 for folder [{}]".format(folder))
    objects_to_delete = s3Client.list_objects(s3Bkt, prefix=folder, recursive=True)
    objects_to_delete = [x.object_name for x in objects_to_delete]
    for del_err in s3Client.remove_objects(s3Bkt, objects_to_delete):
        print("Deletion Error: {}".format(del_err))
    delete_stop = timeit.default_timer()
    delete_time = round(delete_stop - delete_start, 2)
    msg = "s3 folder cleanup time: [{}s]".format(str(delete_time))
    logger.info(msg)
    if (useQ):
        q.put(msg)


    #
    # traverse input dir and upload files
    #
    fileCount = 0
    for r, d, f in os.walk(inputDir):
        if (stopFlag):
            print("stop flag found - break main loop")
            break

        for file in f:
            if (stopFlag):
                print("stop flag found - break")
                break

            fileCount += 1
            fileStartTime = timeit.default_timer()
            inputFile = os.path.join(r, file)
            fileToUpload = inputFile

            # need to make the s3 object name from the filepath
            drive_tail = os.path.splitdrive(inputFile)      # split drive from rest of filename
            inputFileTail = drive_tail[1]
            spos = inputFileTail.find(inputDir)
            epos = spos + len(inputDir)
            newTail = inputFileTail[epos:]
            s3Name = folder + "\\" + newTail
            s3Name = genS3Name(s3Name)

            # if we have been instructed to encrypt
            if encrypt == "true":
                bufferSize = 64 * 1024

                # read file / encrypt file / upload file
                try:
                    with open(inputFile, 'rb') as file_data:
                        #encrypt data
                        fCiph = io.BytesIO()
                        pyAesCrypt.encryptStream(file_data, fCiph, fileEncryptionPass, bufferSize)
                        ctlen = len(fCiph.getvalue())

                        s3Name = s3Name + ".enc"

                        fCiph.seek(0)
                        s3Client.put_object(
                                bucket_name=s3Bkt, 
                                object_name=s3Name, 
                                length=ctlen,
                                data=fCiph
                        )
                except ResponseError as err:
                   logger.error("ERROR: FILE_UPLOAD_ERROR [{}]".format(err))

            else:
                # just copy the file to s3
                try:
                    s3Client.fput_object(s3Bkt, s3Name, fileToUpload)
                except ResponseError as err:
                    logger.error("ERROR: FILE_UPLOAD_ERROR [{}]".format(err))


            # log an entry for progress
            logMod = int(config['LOG']['log.report_interval'])
            if (fileCount % logMod == 0):
                logger.info("fileCount: {} | s3File: [{}]".format(str(fileCount), s3Name))
            
            fileEndTime = timeit.default_timer()
            fileRunTime = round(fileEndTime - fileStartTime, 2)

            # report back to gui
            if (useQ):
                msg = str(fileCount) + "|" + s3Name + "|" + str(fileRunTime) + "s"
                q.put(msg)


    stop = timeit.default_timer()
    runTime = stop - start
    minutes = int(runTime / 60)
    seconds = round(runTime % 60,2)
    logger.info("run complete : runtime : {}m {}s".format(str(minutes), str(seconds)))
    
    if (useQ):
        q.put("Run Complete - run time: {}m {}s".format(minutes, seconds))

# end doBackup



#
# function to perform a restore job
#
def doRestore(restoreDir, folder, q, config, logger, useQ):
    # make sure the restore directory exists
    if not os.path.exists(restoreDir):
        logger.info("making directory: {}".format(restoreDir))
        os.makedirs(restoreDir)
    else:
        logger.info("restoreDirectory: [{}] exists".format(restoreDir))

     # suppress s3 warnings
    warnings.simplefilter('ignore', urllib3.exceptions.SecurityWarning)

    # start timer
    start = timeit.default_timer()

    logger.info("===== STARTING BACKUP RUN =====")

    # config settings for file encryption
    fileEncryptionPass = config['DEFAULT']['file.encryption_password']

    # connect to s3
    s3Host = config['S3']['s3.server']
    s3Access = config['S3']['s3.access_key']
    s3Secret = config['S3']['s3.secret_key']
    s3SslCert = config['S3']['s3.ssl_cacert']
    s3Bkt = config['S3']['s3.bucket_name']
    os.environ['SSL_CERT_FILE'] = s3SslCert
    logger.info("connecting to s3 server: [{}] - access_key: [{}] - secret: [{}]".format(s3Host, s3Access, s3Secret))

    s3Client = Minio(s3Host,
                    access_key=s3Access,
                    secret_key=s3Secret,
                    secure=True)

    # list objects in bucket
    # write each object to a file
    # decrypt if necessary
    objects = s3Client.list_objects(s3Bkt, prefix=folder, recursive=True)
    objectCount = 0
    for obj in objects:
        objectCount += 1
        objName = obj.object_name
        logger.info("{} object name: [{}]".format(objectCount, objName))

        try:
            data = s3Client.get_object(s3Bkt, objName)
        except ResponseError as err:
            print(err)
            logger.error("error fetching object: [{}]".format(err))
            continue

        # convert object name to filename and make sure target directory exists
        filename = restoreDir + "\\" + str(objName)
        filename = filename.replace("/", "\\")    
        tgtDir = os.path.dirname(filename)
        if not os.path.exists(tgtDir):
            os.makedirs(tgtDir)

        # convert httpresponse to BytesIO
        data1 = io.BytesIO(data.read())
        datalen = len(data1.getvalue())
        data1.seek(0)

        # decrypt the file if it is encrypted
        if (filename.endswith(".enc")):
            logger.info("file is encrypted: decrypting")
            bufferSize = 64 * 1024
            decryptedFileName = filename[:-4]
            
            fDec = io.BytesIO()
            pyAesCrypt.decryptStream(data1, fDec, fileEncryptionPass, bufferSize, datalen)

            # new data and filename
            filename = decryptedFileName
            data1 = fDec
            data1.seek(0)
            

        # write object data to a file
        with open(filename, 'wb') as file_data:
            file_data.write(data1.getvalue())

        file_data.close()
        
        if (useQ):
            msg = str(objectCount) + " | object name [{}]".format(objName)
            q.put(msg)
    # end loop

    stop = timeit.default_timer()
    runTime = stop - start
    minutes = int(runTime / 60)
    seconds = round(runTime % 60,2)
    logger.info("run complete : runtime : {}m {}s".format(str(minutes), str(seconds)))
    
    if (useQ):
        q.put("Run Complete - run time: {}m {}s".format(minutes, seconds))

## end doRestore