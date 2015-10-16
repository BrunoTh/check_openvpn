#!/usr/bin/python

import telnetlib
import argparse
import time
import re
from datetime import datetime


def get_data(hostaddress, port, command):
    """
    USES THE OPENVPN MANAGEMENT INTERFACE FOR DATA
    :param hostaddress:
    :param port:
    :param command:
    :return:
    """

    try:
        con = telnetlib.Telnet(hostaddress, int(port), 5)
        con.read_lazy()
        #con.read_until("'help' for more info")
        time.sleep(.1)
        con.write(command + "\n")
        con.write("exit\n")
        res = con.read_all()

        a_res = []
        for line in res.splitlines():
            if re.search("OpenVPN Management Interface", line) or re.search("END", line):
                continue
            a_res.append(line)

        con.close()
        return a_res
    except:
        print "ERROR: Connection to Server failed."
        exit(2)


def receive_data(hostaddress, port, command):
    """
    RETURNS ARRAY WITH REQUESTED DATA AND HAS TIMEOUT
    :param hostaddress:
    :param port:
    :param command:
    :return:
    """

    received = False
    count = 0
    timeout = 10

    while not received and count <= timeout:
        data = get_data(hostaddress, port, command)
        if len(data) >= 1:
            if len(data[0]) >= 1:
                received = True
        count += 1

    if len(data) >= 1 and count <= timeout:
        return data
    else:
        return "ERROR: Could not receive data"


def get_num_connected(hostaddress, port):
    """
    RETURNS THE AMOUNT OF CONNECTED CLIENTS
    :param hostaddress:
    :param port:
    :rtype : int
    :return:
    """

    data = receive_data(hostaddress, port, "load-stats")

    if type(data) is str and data.find("ERROR") >= 0:
        print data
        exit(2)

    work = data[0].split(',')
    work = work[0].split('=')
    return int(work[1])


def get_avgtraffic(hostaddress, port, service, intervall):
    """
    RETURNS THE AVG. OF INCOMING AND OUTGOING TRAFFIC
    :param intervall: in seconds
    :param port:
    :param hostaddress:
    :param service:
    :return:
    """

    open("/tmp/check_openvpn-traffic-%s-%s.tmp" % (service, hostaddress), "a").close()

    with open("/tmp/check_openvpn-traffic-%s-%s.tmp" % (service, hostaddress), "r+") as f:
        temp_data = f.readline()
        empty = False

        if len(temp_data) <= 0:
            old_time = datetime.now()
            old_in = 0
            old_out = 0
            empty = True
        else:
            temp_data = temp_data.split(';')
            old_time = datetime.strptime(temp_data[0], "%Y-%m-%d %H:%M:%S.%f")
            old_in = int(temp_data[1])
            old_out = int(temp_data[2])

        data = receive_data(hostaddress, port, "load-stats")

        if type(data) is str and data.find("ERROR") >= 0:
            print data
            exit(2)

        work = data[0].split(',')
        actual_time = datetime.now()
        actual_in = int(work[1].split('=')[1])
        actual_out = int(work[2].split('=')[1])

        if empty:
            delta_time = 1
            delta_in = 0
            delta_out = 0
        else:
            time_delta = actual_time - old_time
            delta_time = time_delta.seconds + time_delta.microseconds*1E-6
            delta_in = float(actual_in - old_in)
            delta_out = float(actual_out - old_out)

        f.seek(0)
        f.write(str(actual_time) + ";%d;%d" % (actual_in, actual_out))

    if delta_time+4*60 < intervall:
        kb_in = 0
        kb_out = 0
    else:
        kb_in = (delta_in/1024)*intervall/delta_time
        kb_out = (delta_out/1024)*intervall/delta_time

    return float("%.2f" % kb_in), float("%.2f" % kb_out)


def get_momenttraffic(hostaddress, port):
    """
    RETURNS THE AMOUNT OF TRANSFERED DATA
    :param hostaddress:
    :param port:
    :return:
    """

    data = receive_data(hostaddress, port, "load-stats")

    if type(data) is str and data.find("ERROR") >= 0:
        print data
        exit(2)
    
    work = data[0].split(',')
    actual_in = int(work[1].split('=')[1])
    actual_out = int(work[2].split('=')[1])

    return actual_in, actual_out


if __name__ == '__main__':
    argp = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    argp.add_argument('-H', '--hostaddress', help='OpenVPN Server Address')
    argp.add_argument('-p', '--port', help='OpenVPN Server Interface Port')
    argp.add_argument('-C', '--command',
                      help='maxconnections - monitor amount of connections\ntraffic - monitor traffic\nmomenttraffic - transfered MB')
    argp.add_argument('-S', '--service', help='Nagios service name')
    argp.add_argument('-w', '--warning', help='warning threshold')
    argp.add_argument('-c', '--critical', help='critical threshold')
    args = argp.parse_args()

    cmd = args.command.lower()
    warning = float(args.warning)
    critical = float(args.critical)

    # CMD = MAXCONNECTIONS
    if cmd == "maxconnections":
        conns = get_num_connected(args.hostaddress, args.port)

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

    # CMD = TRAFFIC
    elif cmd == "traffic":
        dIn, dOut = get_avgtraffic(args.hostaddress, args.port, args.service, 1)

        performance = "'Incoming'=%.2fKB/s;%d;%d;0; 'Outgoing'=%.2fKB/s;%d;%d;0;" % (
            dIn, warning, critical, dOut, warning, critical)

        if dIn < warning and dOut < warning:
            print "OK: In - %.2f; Out - %.2f |%s" % (dIn, dOut, performance)
            exit(0)
        elif (dIn < critical and dOut < critical) and (dIn >= warning or dOut >= warning):
            print "WARNING: In - %.2f; Out - %.2f |%s" % (dIn, dOut, performance)
            exit(1)
        elif dIn >= critical or dOut >= critical:
            print "CRITICAL: In - %.2f; Out - %.2f |%s" % (dIn, dOut, performance)
            exit(2)

    #CMD = MOMENTTRAFFIC
    elif cmd == "momenttraffic":
        incoming, outgoing = get_momenttraffic(args.hostaddress, args.port)

        in_mb = float(incoming)/1024/1024
        out_mb = float(outgoing)/1024/1024

        performance = "'Incoming'=%.2fMB;;;; 'Outgoing'=%.2fMB;;;;" % (in_mb, out_mb)

        print "OK: In - %.2fMB; Out - %.2fMB |%s" % (in_mb, out_mb, performance)
        exit(0)

    exit(3)
