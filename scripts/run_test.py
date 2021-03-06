#!/usr/bin/env python
#
# Main script for running RAISHIN.
#
# Usage: 
#   run.py <NDIM> <NCORES> 
#
#	where
#		NDIM: number of dimensions
#		NCORES: number of CPUs (MPI) 
#
# Run this in the folder which will store the simulation results.
#
# Output files:
# - run.log: holds full output from code
# - time.log: times and snapshots (for plotting)
# - restartNNN.outdat: output data for restart from the CPUs
# - structrNNN_MMM.outdat: output from each CPU (NNN) and time (MMM)
#
# Requirements:
# - RAISHIN of course, with configuration files properly set up
# - Nemmen python module available at https://github.com/rsnemmen/nemmen 
# - Fish module, availabe via `pip install fish`


import math, sys
import shutil, subprocess, re, time, datetime, os, glob
import nemmen.misc, fish

tic=time.time() # begin timing

# ASCII art from http://ascii.co.uk/art/lightning
print("                    ,/")
print("                  ,'/")
print("                ,' /")
print("              ,'  /_____,")
print("            .'____    ,'    RAISHIN")
print("                 /  ,'")
print("                / ,'")
print("               /,'")
print("              /'")





############# COMMAND-LINE ARGUMENTS
# check if there were command-line arguments
if len(sys.argv)==3: # there are command-line arguments that were actually typed
	ndim= int(sys.argv[1])
	ncpu = int(sys.argv[2])
else: # there is nothing
	print('Usage: \nrun.py <NDIM> <NCORES>')
	sys.exit(0)




############# CPU SPLITTING 
# determines splitting of computational mesh for MPI
# careful: imperfect splitting, can be improved
if ndim==1:	# 1D 
	ni=ncpu
	nj=1
	nk=1
elif ndim==2:	# 2D in i,k
	ni=int(round(math.sqrt(ncpu)))
	nj=1
	nk=int(round(ncpu/float(ni)))
	ncpu=ni*nk  # not necessarily equal to the input ncpu
elif ndim==3:	# 3D
	ni=int(round(ncpu**(1./3.)))
	nj=ni
	nk=int(round(ncpu/(float(ni)*nj)))
	ncpu=ni*nj*nk   # not necessarily equal to the input ncpu



############# READS/UPDATES PARAMETER FILE
# http://stackoverflow.com/questions/39086/search-and-replace-a-line-in-a-file-in-python
#
# input will be superseded eventually by a python configuration file
# instead of pram.f90

shutil.copy("pram.f90","pram.f90.bak") # backup copy
f = open("pram.f90.bak","r")
newf=open("pram.f90", "w")	# replaces parameter file

for line in f:
	if 'iprocs' in line:	# sets right number of CPUs
		newf.write("  integer, parameter :: iprocs="+str(ni)+", jprocs="+str(nj)+", kprocs="+str(nk)+" !- CPU number in i-,j-, and  k- direction\n")
	else:
		newf.write(line)

	# gets tmax
	if re.search(r' tmax=\d+\.\d+d', line):
		tmax=re.search(r'\d+\.\d+d0', line).group()
		tmax=float(re.sub(r"d", "e", tmax)) # replaces d with e in the number for use in python

	# gets nshot
	if re.search(r' nshot=\d+', line):
		nshot=re.search(r'\d+', line).group()
		
f.close()
newf.close()

shutil.copy("convert_vtk2dn1.f90","convert_vtk2dn1.f90.bak") # backup copy
f = open("convert_vtk2dn1.f90.bak","r")
newf=open("convert_vtk2dn1.f90", "w")	# replaces parameter file

for line in f:
	if 'integer, parameter :: ns' in line:	# sets right number of VTK snapshots
		newf.write("  integer, parameter :: ns=0, ne="+nshot+" ! start and end data file number\n")
	else:
		newf.write(line)
		
f.close()
newf.close()

print("Updated parameter file \n")



############# COMPILATION
shutil.copy("Makefile_xgrmhd","Makefile")
subprocess.call("make clean".split())	# make clean
nemmen.misc.runsave("make","make.log")	# make
#subprocess.call("make".split())
print("Compiled \n")

# removes previous datafiles
subprocess.Popen("rm -f restart*.outdat struct*.outdat ok*.vtk", shell=True)





############# RUN
# create log files
logfile = open("run.log", "w")
timefile=open("time.log", "w")
errfile = open("errors.log", "w")

print("Beginning execution with "+str(ncpu)+" CPUs at "+str(datetime.datetime.now())+"\n")
p = subprocess.Popen('mpiexec -n '+ str(ncpu) +' ./xgrmhd.exe', stdout = subprocess.PIPE, stderr = errfile, shell = True)
#p = subprocess.Popen('mpiexec -n '+str(ncpu)+ ' ./xgrmhd.exe | tee log.dat ', stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True)






############# PROGRESS BAR / LOG
peixe = fish.ProgressFish(total=tmax) # Progress bar initialization
j=0

while True:
	line = p.stdout.readline() # output from run, line by line real time
	linespl=line.split() # for pattern matching below

	logfile.write(line)	# updates log file

	# updates progress bar based on time 
	if "time=" in linespl: 
		i=linespl.index("time=")
		t=round(float(linespl[i+1]),2)	# trick to get current time of simulation
		peixe.animate(amount=t)

	# updates time log file for snapshots
	if (len(linespl)==2) and ("time=" in linespl):
 		timefile.write(str(j) +"\t"+ linespl[1] + "\n")	
 		j=j+1

	if not line: break # ends at end-of-file






############# CREATES VTK FILES
# compiles and runs convert to create snapshots

shutil.copy("Makefile_convert","Makefile")
subprocess.call("make clean".split())	# make clean
nemmen.misc.runsave("make","make_vtk.log")	# make
subprocess.call("./xconvert.exe".split())
print("Created VTK files \n")



#####################################################
#                                                   #
#  The following two routines make it easier to     #
#  organize data once the simulations are finished  #
#                                                   #
#####################################################

############# STORES VTK FILES IN FOLDER "results"

# Path to be created

here    = os.getcwd()
results = (here+"/results/")

os.mkdir(results, 0777)

for vtkfile in glob.iglob(os.path.join(here, "*.vtk")):
    shutil.move(vtkfile, results)

############# STORES PARAMETER FILES IN FOLDER "params"

here   = os.getcwd()
params = (here+"/params/")

os.mkdir(params, 0777)

shutil.copy("pram.f90", params)
shutil.copy("convert_vtk2dn1.f90", params)
shutil.copy("mdgrmhd.f90", params)



############# FINISH
logfile.close()
timefile.close()
errfile.close()

# print time elapsed
print("Finished at "+ str(datetime.datetime.now()) +"\n")

t=time.time() - tic # end timing
print("Time elapsed = "+str(round(t/60.,1)) +" min")

