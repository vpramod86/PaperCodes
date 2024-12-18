"""
Computes the projections of the instantaneous (time-evolved) KS states onto the initial (GS) KS states
matrx[t,i,j,:] = <phi_i(t)|phi_j(0)> a complex matrix.
"""
import sys
import math
import os
import errno
import numpy as np
import re
import copy
from oct_projections import Projections
import binner
from numpy import fft

### Computes the time-dependent populations of the t=0 K-S states
### and optionally, the excited DOS for various time steps
### and the time-dependent occupied manifold recovery
### Input file "read_proj.inp" is taken as parameter
### variables are explained below and in the input file

#### Function to create directories
def check_and_create(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

#### Function to read in the input parameter file ####

def read_input(lines):

        nocc = 10
        nunocc = 10
        nt = 1
        nskp = 1
        nbeg = 1
        nproj = nocc+nunocc
        tpop = True
        tdmat = True
        tdos = True
        axis = [0, 0, 1]
        evfile = "info"
        ni = 5
        na = 5
        evals = []
        iproj = []
        dosdir = ""
        ef = 0.0
        emin = 0.0
        emax = 0.0
        esig = 0.1
        ne = 1

        for line in lines:
                tnocc = re.search("occ",line,re.I)
                tnunocc = re.search("unocc",line,re.I)
                tnt = re.search("nt",line,re.I)
                tnskp = re.search("nskp",line,re.I)
                tnbeg = re.search("nbeg",line,re.I)
                tnproj = re.search("nproj",line,re.I)
                tiproj = re.search("iproj",line,re.I)
                tpop = re.search("pop",line,re.I)
                tdmat = re.search("dmat",line,re.I)
                tdos = re.search("dos",line,re.I)
                tni = re.search("ni",line,re.I)
                tna = re.search("na",line,re.I)
                taxis = re.search("axis",line,re.I)
                tevf = re.search("evfile",line,re.I)
                tehrange = re.search("EHR",line,re.I)
		
                if tnocc:
                        arr = line[tnocc.end():].strip().split()
                        nocc = int(arr[0])

                if tnunocc:
                        arr = line[tnunocc.end():].strip().split()
                        nunocc = int(arr[0])
		
                if tnt:
                        arr =  line[tnt.end():].strip().split()
                        nt = int(arr[0])

                if tnskp:
                        arr =  line[tnskp.end():].strip().split()
                        nskp = int(arr[0])

                if tnbeg:
                        arr =  line[tnbeg.end():].strip().split()
                        nbeg = float(arr[0])

                if tdos:
                        tpop = True
                        tdmat = True
                        arr = line[tdos.end():].strip().split()
                        for i in range(len(arr)):
                                item = arr[i]
                                if re.search("emin",item,re.I):
                                        emin = float(arr[i+1])
                                elif re.search("emax",item,re.I):
                                        emax = float(arr[i+1])
                                elif re.search("ef",item,re.I):
                                        ef = float(arr[i+1])
                                elif re.search("esig",item,re.I):
                                        esig = float(arr[i+1])
                                elif re.search("ne",item,re.I):
                                        ne = int(arr[i+1])
                                elif re.search("dir",item,re.I):
                                        dosdir = arr[i+1].strip()
			
                        print("Evolving DOS calculation requested with parameters:")
                        print(emin, emax, ef, esig, ne, dosdir)
										
                        if tnproj:
                                arr =  line[tnproj.end():].strip().split()
                                nproj = int(arr[0])

                if tiproj:
                        arr =  line[tiproj.end():].strip().split()
                        i=0
                        for x in arr:
                                if "-" in x:
                                    arr1=x.split('-')
                                    ibeg = int(arr1[0])
                                    iend = int(arr1[1])
                                    for k in range(ibeg,iend+1):
                                        iproj.append(k-1)
                                        i += 1
                                else:
                                    iproj.append(int(x)-1)
                                    i += 1
		
                if tni:
                        arr =  line[tni.end():].strip().split()
                        ni = int(arr[0])

                if tna:
                        arr =  line[tna.end():].strip().split()
                        na = int(arr[0])

                if taxis:
                        arr =  line[taxis.end():].strip().split()
                        axis = [int(arr[0]), int(arr[1]), int(arr[2])]

                if tevf:
                        arr = line[tevf.end():].strip().split()
                        evfile = arr[0]

                if tehrange:
                        arr = line[tehrange.end():].strip().split()
                        hlmin = arr[0]
                        elmax = arr[1]

        fn = open(evfile,"r")
        recs = fn.readlines()
        ctr = 0
        for line in recs:
                if re.search("occupation",line,re.I):
                        ctrbeg = ctr
                        break
                ctr += 1

        ist = 0
        for line in recs[ctrbeg+1:]:
                if ist == (nocc+nunocc):
                        break
                evals.append(float(line.strip().split()[2]))
                ist += 1

        if tehrange:
                ni = 0
                na = 0
                ehomo = evals[nocc-1]
                for en in evals:
                        ediff = en-ehomo
                        if en <= ehomo and en >= hlmin:
                                ni += 1
                        elif en > homo and en <= elmin:
                                na += 1

                ni = min([ni,nocc])
                na = min([na,nunocc])

        return (nocc, nunocc, nt, nbeg, nskp, axis, ni, na, tpop, tdos, ef, emin, emax, ne, esig, dosdir, tdmat, nproj, iproj, evals)

### Main code begins ####
#fname=sys.argv[1]
fname='My_tdden.inp'
fp=open(fname,"r")
lines=fp.readlines()
fp.close()
(nocc, nunocc, nt, nbeg, nskp, axis, nhole, npart, tpop, tdos, ef, emin, emax, ne, esig, dosdir, tdmat, nproj, iproj, ener) = read_input(lines)

##### Instantiate an object of the Projections class
TDsystem=Projections(nt,nocc,nunocc)

#### Extract octopus projections into the object
fp=open("projections","r")
(kick, delt) =TDsystem.extract(fp,nbeg)
fp.close()
print("Projections extracted from file!")
print("Kick is :", kick)
print("Time step is :", delt)

#### Compute the TD populations of the initial KS states
if tpop:
        popln = np.zeros((nproj,nt),dtype=float)
        popln = TDsystem.populations(iproj)

        fp=open("populations.dat","w")
        TDsystem.write_pop(popln,fp)
        fp.close()

        if tdos:
                print("Creating DOS files...")
                dname = "./"+dosdir
                check_and_create(dname)

                fn = dname+'/dos'

                enef = []
                for e in ener:
                        enef.append(e-ef)

                for it in range(nt):
                        a=np.vstack((enef,popln[:,it])).T
                        ados=binner.binit(a,emin,emax,ne,esig)
                        if it == 0:
                                ados0=copy.copy(ados)
                        for ie in range(ne):
                                ados[ie,1] = ados[ie,1]-ados0[ie,1]				

                        fname=fn+'_'+str(it)+'.dat'
                        fp=open(fname,"w")
                        for (e,dos) in ados:
                                fp.write("%10.6f  %10.6f\n" %(e,dos))
                        fp.close()
                        print("Written ",fname)

#### Compute the TD density matrix in terms of the occupied and unoccupied states
if tdmat:

         (stocc, stunocc, t, dmat) = TDsystem.denmat(nhole,npart)
       
         enocc = []
         enuocc = []
       
         for ix in stocc:
                 enocc.append(ener[ix])
       
         for ix in stunocc:
                 enuocc.append(ener[ix])
       
         fp=open("dmat.dat","w")	
         TDsystem.write_dmat(t,dmat,enocc,enuocc,fp)
         fp.close()
       
         nus, dmatw, strengthKS, transwt, strength = TDsystem.ft_dmat(dmat.real,stocc,stunocc,axis)
       
         nus = 2.0*np.pi*nus  ## Convert to omega
       
	   
         fp=open("dmatw.dat","w")
         TDsystem.write_dmat(nus,dmatw,enocc,enuocc,fp)
         fp.close()
       
         fp=open("strength.dat","w")
         TDsystem.write_dmat(nus,strengthKS,enocc,enuocc,fp)
         fp.close()
       
         fp=open("transwt.dat","w")
         TDsystem.write_dmat(nus,transwt,enocc,enuocc,fp)
         fp.close()
       
#######  Plot the particle-hole resolved strength function 
         fp=open("spectrum_prop.dat","w")
         for iw in range(nt):
              fp.write("%10.6f %10.6f \n" %(nus[iw],strength[iw]))
         fp.close()

