#!/usr/bin/python

import telnetlib
import argparse
import time
import re
from datetime import datetime

argp = argparse.ArgumentParser()
argp.add_argument('-H', '--hostaddress', help='OpenVPN Server Address')
argp.add_argument('-p', '--port', help='OpenVPN Server Interface Port')
argp.add_argument('-C', '--command', help='')
argp.add_argument('-S', '--service', help='Nagios service name')
argp.add_argument('-w', '--warning', help='')
argp.add_argument('-c', '--critical', help='')
#argp.add_argument('-C', '--command', help='OpenVPN Management Interface Command')
args = argp.parse_args()

#USES THE OPENVPN MANAGEMENT INTERFACE FOR DATA
def getData(command):
    con = telnetlib.Telnet(args.hostaddress, int(args.port))
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


#RETURNS THE AMOUNT OF CONNECTED CLIENTS
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
    

#RETURNS THE AVG. OF INCOMING AND OUTGOING TRAFFIC
def getTraffic():
    f = open("/tmp/check_openvpn-traffic-%s-%s.tmp" % (args.service, args.hostaddress), "a")
    f.close()
    
    f = open("/tmp/check_openvpn-traffic-%s-%s.tmp" % (args.service, args.hostaddress), "r+")
    tData = f.readline()
    empty = False
    
    if len(tData) <= 0:
        oTime = datetime.now()
        oIn = 0
        oOut = 0
        empty = True
    else:
        tData = tData.split(';')
        oTime = datetime.strptime(tData[0], "'%Y-%m-%d %H:%M:%S.%f'")
        oIn = int(tData[1])
        oOut = int(tData[2])
    
    data = []
    while len(data) <= 0:
        data = getData("load-stats")
    work = data[0].split(',')
    aTime = datetime.now()
    aIn = int(work[1].split('=')[1])
    aOut = int(work[2].split('=')[1])
    
    if empty:
        dTime = 1
        dIn = 0
        dOut = 0
    else:
        dTime = float((aTime - oTime).total_seconds())
        dIn = float(aIn - oIn)
        dOut = float(aOut - oOut)
    
    f.seek(0)
    f.write(`str(aTime)` + ";%d;%d" % (aIn, aOut))
    f.close()
    
    return float("%.2f" % ((dIn/1024)/dTime)), float("%.2f" % ((dOut/1024)/dTime))




cmd = args.command.lower()
warning = float(args.warning)
critical = float(args.critical)

#CMD = MAXCONNECTIONS
if cmd == "maxconnections":
    conns = getNumConnected()
    
    performance = "'Connections'=%d;%.0f;%.0f;0;" % (conns, warning, critical)
    
    if conns == 1:
        output = "Currently is %d user connected. |%s" % (conns, performance)
    else:
        output = "Currently are %d users connected. |%s" % (conns, performance)
    
    if conns < warning:
        print "OK: %s" % output
        exit(0)
    elif conns < critical:
        print "WARNING: %s" % output
        exit(1)
    elif conns >= critical:
        print "CRITICAL: %s" % output
        exit(2)
        
#CMD = TRAFFIC        
elif cmd == "traffic":
    dIn, dOut = getTraffic()
    
    performance = "'Incoming KB/s'=%.2f;%d;%d;0; 'Outgoing KB/s'=%.2f;%d;%d;0;" % (dIn, warning, critical, dOut, warning, critical)
    
    if dIn < warning and dOut < warning:
        print "OK: In - %.2f; Out - %.2f |%s" % (dIn, dOut, performance)
        exit(0)
    elif (dIn < critical and dOut < critical) and (dIn >= warning or dOut >= warning):
        print "WARNING: In - %.2f; Out - %.2f |%s" % (dIn, dOut, performance)
        exit(1)
    elif dIn >= critical or dOut >= critical:
        print "CRITICAL: In - %.2f; Out - %.2f |%s" % (dIn, dOut, performance)
        exit(2)

exit(3)
