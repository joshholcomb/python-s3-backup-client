from tkinter import (Tk, BOTH, Text, E, W, S, N, END, 
    NORMAL, DISABLED, StringVar, IntVar, HORIZONTAL, VERTICAL)
from tkinter.ttk import Frame, Label, Button, Progressbar, Entry, Radiobutton, Checkbutton, OptionMenu, Separator
from tkinter import scrolledtext
from tkinter import filedialog
from tkinter import messagebox

from multiprocessing import Queue
import threading
from queue import Empty
from decimal import Decimal, getcontext
import os
import sys
import configparser                     # for parsing the config file
import timeit                           # for timing program runtime
import backup_util
import logging

DELAY1 = 100
DELAY2 = 100

# Queue must be global
q = Queue()

# load configuration
config = configparser.ConfigParser()
found = config.read('config/bkup.conf')
if (len(found) == 0):
    print("could not load config.")
    sys.exit(1)

if not os.path.exists("./logs"):
        os.makedirs("./logs")

 # setup a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = logging.FileHandler('./logs/backup_client.log')
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)


# class for gui
class GUI(Frame):
  
    def __init__(self, parent):
        Frame.__init__(self, parent, name="frame")        
        self.parent = parent
        self.initUI()
                
    def getFilePath (self):
        currdir = os.getcwd()
        tempdir = filedialog.askdirectory(master=self, 
            initialdir=currdir, title='Please select a directory')
        self.ent1.delete(0, END)
        self.ent1.insert(0, tempdir)

    def initUI(self):
        self.parent.title("backup client")
        self.pack(fill=BOTH, expand=True)

        self.grid_columnconfigure(6, weight=1)
        self.grid_rowconfigure(9, weight=1)
        
        # display config info
        f1 = Frame(self)
        lblConfig = Label(f1, text="Config Settings:")
        txtConfig = Text(f1, height=4, width=40)
        s3Host = config['S3']['s3.server']
        msg = "s3.server: " + s3Host
        txtConfig.insert('end', msg)
        txtConfig.configure(state='disabled')
        f1.grid(row=0, column=0, sticky="nsew")
        lblConfig.pack(side="top", anchor="w", padx=10)
        txtConfig.pack(side="top", anchor="w", padx=10)

        # run timer
        fTimer = Frame(self)
        lbl3 = Label(fTimer, text="Run Time: ")
        self.lbl4 = Label(fTimer, text="N/A")
        fTimer.grid(row=0, column=1, sticky=W, padx=20, pady=20)
        lbl3.pack(side="top")
        self.lbl4.pack(side="top")

        # backup / restore radio button
        fRadio = Frame(self)
        self.br = StringVar(fRadio, "backup")
        lblJobType = Label(fRadio, text="Job Type:")
        self.rbBackup = Radiobutton(fRadio, text="backup", 
            variable=self.br, value="backup", command=self.onSelectRadio)
        self.rbRestore = Radiobutton(fRadio, text="restore", 
            variable=self.br, value="restore", command=self.onSelectRadio)
        fRadio.grid(row=0, column=2, sticky=W)
        lblJobType.pack(side="top")
        self.rbBackup.pack(side="left")
        self.rbRestore.pack(side="left")
        

        sp1 = Separator(self, orient=HORIZONTAL)
        sp1.grid(row=3, column=0, columnspan=5, sticky='ew', padx=10, pady=20)

        # inputDir entry with FileDialog
        f2 = Frame(self)
        lblSrc = Label(f2, text="SOURCE INFO")
        self.lbl1 = Label(f2, text="Src Directory:")
        self.ent1 = Entry(f2, width=40)
        b1 = Button(f2, text="Browse", width=8, command=self.getFilePath)
        f2.grid(row=4, column=0, sticky=W, padx=10, pady=10)
        lblSrc.pack(side="top")
        self.lbl1.pack(side="top", anchor=W)
        self.ent1.pack(side="left", anchor=W)
        b1.pack(side="left", anchor=E)
        
        # vertical separator
        sp3 = Separator(self, orient=VERTICAL)
        sp3.grid(row=4, column=1, sticky='ns', padx=20, pady=10, rowspan=2)

        # s3 bucket selection
        fBucket = Frame(self)
        lblTgt = Label(fBucket, text="TARGET INFO")
        lblBucket = Label(fBucket, text="S3 bucket:")
        buckets = backup_util.getBucketList(config)
        
        options = list()
        self.selectedBucket = StringVar(fBucket)
        for bucket in buckets:
            options.append(bucket.name)
        self.bucketMenu = OptionMenu(fBucket, self.selectedBucket, *options)
        self.bucketMenu.config(width=30)
        fBucket.grid(row=4, column=2, sticky=W, padx=10, pady=10)
        lblTgt.pack(side="top")
        lblBucket.pack(side="top", anchor=W)
        self.bucketMenu.pack(side="top")

        # s3 folder entry
        f3 = Frame(self)
        lblFolder = Label(f3, text="S3 Folder:")
        self.ent2 = Entry(f3, width=20)
        f3.grid(row=5, column=2, sticky=W, padx=10)
        lblFolder.pack(side="top", anchor=W)
        self.ent2.pack(side="top", anchor=W)

        sp2 = Separator(self, orient=HORIZONTAL)
        sp2.grid(row=6, column=0, columnspan=5, sticky='ew', padx=10, pady=20)

        # buttons (backup/stop/reset/restore)
        fButtons = Frame(self)
        self.backupBtn = Button(fButtons, text="Backup", command=self.onBackup)
        self.restoreBtn = Button(fButtons, text="Restore", command=self.onRestore)
        self.stopBtn = Button(fButtons, text="Stop", command=self.onStop)
        self.resetBtn = Button(fButtons, text="Reset", command=self.onResetBtn)
        fButtons.grid(row=7, column=0, sticky=W, padx=10, pady=10)
        self.backupBtn.pack(side="left")
        self.restoreBtn.pack(side="left")
        self.restoreBtn.config(state=DISABLED)
        self.stopBtn.pack(side="left")
        self.resetBtn.pack(side="left")

        # progress bar
        self.pbar = Progressbar(self, mode='indeterminate')        
        self.pbar.grid(row=7, column=1, columnspan=1, sticky=W+E)   

        # a couple of checkbox items
        fchkbox = Frame(self)
        self.quitOnEnd = IntVar(fchkbox, 0)
        self.chkboxQuitOnEnd = Checkbutton(fchkbox, text="quit upon completion", 
            variable=self.quitOnEnd, command=self.onSelectedQoe)
        
        self.doEncrypt = IntVar(fchkbox, 1)
        self.chkboxEncrypt = Checkbutton(fchkbox, text="encrypt data",
            variable=self.doEncrypt, command=self.onCheckEncrypt)

        fchkbox.grid(row=7, column=2, sticky=W, padx=10)
        self.chkboxQuitOnEnd.pack(side="top", anchor="w")
        self.chkboxEncrypt.pack(side="top", anchor="w")

        # scrolled txt
        f4 = Frame(self)
        f4.grid_columnconfigure(1, weight=1)
        f4.grid(row=8, column=0, columnspan=7, rowspan=5, padx=10, pady=10, sticky=(N, E, S, W))
        lblStatus = Label(f4, text="//Job Status//")
        self.txt = scrolledtext.ScrolledText(f4)
        lblStatus.pack(side="top")
        self.txt.pack(side="top", fill=BOTH, expand=True)
       
        # check to make sure we could list the buckets
        if (len(buckets) == 0):
            messagebox.showerror(title="bucket error", message="could not list buckets")


    def onCheckEncrypt(self):
        print("doEncrypt: [{}]".format(self.doEncrypt.get()))

    def onSelectedQoe(self):
        print("quitOnEnd: [{}]".format(self.quitOnEnd.get()))

    def onSelectRadio(self):
        # set value of lbl for inputDir
        if (self.br.get() == "restore"):
            self.lbl1.config(text="Restore Directory:")
            self.backupBtn.config(state=DISABLED)
            self.restoreBtn.config(state=NORMAL)
        else:
            self.lbl1.config(text="Input Directory:")
            self.backupBtn.config(state=NORMAL)
            self.restoreBtn.config(state=DISABLED)
    
    #
    # start button clicked
    #
    def onBackup(self):
        backup_util.stopFlag = False

        # check to make sure we have values
        if (not self.ent1.get()):
            messagebox.showerror("Error", "inputDir is empty")
            return

        if (not self.ent2.get()):
            messagebox.showerror("Error", "s3Folder is empty")
            return
        
        inputDir = str(self.ent1.get())
        folder = str(self.ent2.get())
        
        # start timer
        self.starttime = timeit.default_timer()
        self.backupBtn.config(state=DISABLED)
        self.txt.delete("1.0", END)
        
        useQ = True
        self.t = ThreadedBackupTask(inputDir, 
                    folder, 
                    q, 
                    config, 
                    logger, 
                    useQ, 
                    self.doEncrypt.get(),
                    self.selectedBucket.get())
        self.t.start()
        
        # start progress bar
        self.pbar.start(DELAY2)

        # look for values
        self.after(DELAY1, self.onGetValue)


    #
    # restore button clicked
    #
    def onRestore(self):
        backup_util.stopFlag = False

        # check to see if we have input data
        if (not self.ent1.get()):
            messagebox.showerror("Error", "inputDir is empty")
            return

        if (not self.ent2.get()):
            messagebox.showerror("Error", "s3Folder is empty")
            return
        
        inputDir = str(self.ent1.get())
        folder = str(self.ent2.get())
        
        # start timer
        self.starttime = timeit.default_timer()
        self.restoreBtn.config(state=DISABLED)
        self.backupBtn.config(state=DISABLED)
        self.txt.delete("1.0", END)
        
        useQ = True
        self.t = ThreadedRestoreTask(inputDir, folder, q, config, logger, useQ, self.selectedBucket.get())
        self.t.start()
    
        # start progress bar & look for values
        self.pbar.start(DELAY2)
        self.after(DELAY1, self.onGetValue)

    def onStop(self):
        backup_util.stopFlag = True
        print("set stop flag: {}".format(str()))
        self.t.join()
        self.onGetValue()

    def onResetBtn(self):
        self.ent1.delete(0, END)
        self.ent2.delete(0, END)
        self.txt.delete("1.0", END)
        self.backupBtn.config(state=NORMAL)
        self.restoreBtn.config(state=DISABLED)
        self.br.set("backup")
        self.lbl1.config(text="inputDir:")


    # get values from q
    def onGetValue(self):
        # get some timing
        self.checktime = timeit.default_timer()
        runTime = self.checktime - self.starttime
        minutes = int(runTime / 60)
        seconds = round(runTime % 60,0)
        msg = "{}m {}s".format(minutes, seconds)
        self.lbl4.config(text=msg)

        try:
            while(q.qsize() > 0):
                msg = q.get(0)
                lines = int(self.txt.index('end').split('.')[0]) - 1
                if (lines > 500):
                    self.txt.delete('1.0', '2.0')

                self.txt.insert('end', msg)
                self.txt.insert('end', "\n")
                self.txt.yview('end')
        except Empty:
            print("queue is empty")

        # if process is still alive - set timer and go again
        if (self.t.is_alive()):
            self.after(DELAY1, self.onGetValue)
            return
        else:    
            self.pbar.stop()
            self.backupBtn.config(state=NORMAL)
            self.restoreBtn.config(state=DISABLED)

            if (self.quitOnEnd.get() == 1):
                sys.exit(0)

            
#
# class for backup task
#
class ThreadedBackupTask(threading.Thread):
    def __init__(self, inputDir, folder, q, config, logger, useQ, doEncrypt, bucket):
        threading.Thread.__init__(self)
        self.inputDir = inputDir
        self.folder = folder
        self.q = q
        self.config = config
        self.logger = logger
        self.useQ = useQ
        self.doEncrypt = doEncrypt
        self.bucket = bucket

    def run(self):
        backup_util.doBackup(self.inputDir, self.folder, 
            self.q, self.config, self.logger, self.useQ, self.doEncrypt, self.bucket)

#
# class for restore task
#
class ThreadedRestoreTask(threading.Thread):
    def __init__(self, inputDir, folder, q, config, logger, useQ, bucket):
        threading.Thread.__init__(self)
        self.inputDir = inputDir
        self.folder = folder
        self.q = q
        self.config = config
        self.logger = logger
        self.useQ = useQ
        self.bucket = bucket

    def run(self):
        backup_util.doRestore(self.inputDir, self.folder, 
            self.q, self.config, self.logger, self.useQ, self.bucket)


def main():  
    root = Tk()
    root.geometry("800x800")
    GUI(root)
    root.mainloop()  


if __name__ == '__main__':
    main()  