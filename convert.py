#!/usr/bin/env python
#
# After you ran RAISHIn, this script takes the files
# generated by many threads and creates VTK files.
#
# Requirements:
# - RAISHIN output data 
# - nmmn python module available at https://github.com/rsnmmn/nmmn
# - Fish module, availabe via `pip install fish`
#

import shutil, subprocess
import nmmn.misc







############# CREATES VTK FILES
# compiles and runs convert to create snapshots

shutil.copy("Makefile_convert","Makefile")
subprocess.call("make clean".split())	# make clean
nmmn.misc.runsave("make","make_vtk.log")	# make
subprocess.call("./xconvert.exe".split())
print("Created VTK files \n")




