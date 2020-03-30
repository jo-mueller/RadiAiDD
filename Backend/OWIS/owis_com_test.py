# -*- coding: utf-8 -*-
"""
Created on Tue Aug  7 13:35:10 2018

@author: InVivoControl

slaveIE = 00 = vertical
slaveID = 04 = horizontal

00INIT1 to initialize
00PSET1=50000 to set move
00PGO1 to move

"""

import serial

serial.Serial()

with serial.Serial("Com5",baudrate=9600,
                          bytesize=serial.EIGHTBITS,
                          parity=serial.PARITY_NONE,
                          stopbits=serial.STOPBITS_ONE,
                          rtscts=False,
                          xonxoff=True,
                          timeout=1,
                          writeTimeout=1) as serialCon:



#    for i in range(0,4):
    #print("testing ID: "+str(i))
    i=0
    request = ("MOFF1\r\n".format(i)).encode(encoding="ASCII")
    print(request.decode())
    
    #print(request)
    
    serialCon.write(request)
    
    asw = (serialCon.read(1024)).decode()
    
    if asw != "":
        print(asw)

serialCon.close()















