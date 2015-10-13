#!/usr/bin/python

import telnetlib
import argparse
import time
import re
from datetime import datetime

argp = argparse.ArgumentParser()
argp.add_argument('-H', '--host', help='OpenVPN Server Address')
argp.add_argument('-p', '--port', help='OpenVPN Server Interface Port')
argp.add_argument('-C', '--command', help='')
argp.add_argument('-w', '--warning', help='')
argp.add_argument('-c', '--critical', help='')
#argp.add_argument('-C', '--command', help='OpenVPN Management Interface Command')
args = argp.parse_args()

def getData(command):
    con = telnetlib.Telnet(args.host, int(args.port))
    con.read_eager()
    time.sleep(.1)
    con.write(command + "\n")
    con.write("exit\n")
    #time.sleep(.2)
    res = con.read_all()
    
    a_res = []
    for line in res.splitlines():
        if re.search("OpenVPN Management Interface", line) or re.search("END", line):
             continue
        a_res.append(line)
    
    con.close()
    return a_res

def getNumConnected():
    data = []
    while len(data) <= 0:
        data = getData("load-stats")
    
    if len(data) <= 0:
        print "Connection to Server failed!"
        exit(3)
    
    work = data[0].split(',')
    work = work[0].split('=')
    return int(work[1])
    

def getTraffic():
    f = open("check_openvpn_traffic.tmp", "r+")
    tData = f.readline().split(';')
    oTime = tData[0]
    oIn = tData[1]
    oOut = tData[2]
    
    data = []
    while len(data) <= 0:
        data = getData("load-stats")
    work = data[0].split(',')
    aTime = 
    aIn = work[1].split('=')[1]
    aOut = work[2].split('=')[2]


cmd = args.command.lower()

if cmd == "maxconnections":
    conns = getNumConnected()
    
    performance = "'Connection(s)'=%d;%d;%d" % (conns, int(args.warning), int(args.critical))
    
    if conns == 1:
        output = "Currently is %d user connected. |%s" % (conns, performance)
    else:
        output = "Currently are %d users connected. |%s" % (conns, performance)
    
    if conns < int(args.warning):
        print "OK: %s" % output
        exit(0)
    elif conns < int(args.critical):
        print "WARNING: %s" % output
        exit(1)
    elif conns >= int(args.critical):
        print "CRITICAL: %s" % output
        exit(2)
elif cmd == "traffic":
    dIn, dOut = getTraffic()

exit(3)
