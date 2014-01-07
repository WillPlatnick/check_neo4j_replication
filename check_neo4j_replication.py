#!/usr/bin/env python
'''
Project     :       Icinga/Nagios plugin to detect neo4j replication delays
Version     :       0.1
Author      :       Will Platnick <wplatnick@gmail.com>
Summary     :       This program is an icinga/nagios plugin to detect neo4j replication delays.
Dependency  :       Python 2.6, Linux, Icinga/Nagios, https://github.com/tempspace/jmxquery

Usage :
```````
shell> python check_neo4j_replication.py -H 1.1.1.1,2.2.2.2,3.3.3.3 -w 3 -c 5
'''

import os
import sys
import subprocess
from optparse import OptionParser

transactions = []
status_string = ""

check_jmx_path = os.path.dirname(os.path.realpath(__file__)) + "/check_jmx"

# Command Line Parsing Arguements
cmd_parser = OptionParser(version = "0.1")
cmd_parser.add_option("-H", "--hosts", type="string", action = "store", \
    dest = "hosts", help = "Hosts to query, comma separated", metavar = "Hosts")
cmd_parser.add_option("-p", "--port", type="string", action = "store", \
    dest = "port", help = "JMX Port", metavar = "Port", default="3637")
cmd_parser.add_option("-w", "--warn", type="string", action = "store", \
    dest = "warn", help = "Number of transactions behind to throw warning", \
    metavar = "Integer")
cmd_parser.add_option("-c", "--critical", type="string", action = "store", \
    dest = "critical", help = "Number of transactions behind to throw critical", \
    metavar = "Integer")
(cmd_options, cmd_args) = cmd_parser.parse_args()

# Check the Command syntax
if not (cmd_options.hosts and cmd_options.warn and cmd_options.critical):
    cmd_parser.print_help()
    sys.exit(3)

hosts = cmd_options.hosts.split(',')
for host in hosts:
    service_string = "service:jmx:rmi:///jndi/rmi://" + host + ":" + cmd_options.port + "/jmxrmi"
    command = [ check_jmx_path, '-U', service_string, '-O', 'org.neo4j:instance=kernel#0,name=High Availability', '-A', 'LastCommittedTxId' ]
    try:
        child = subprocess.Popen(command, stdout=subprocess.PIPE)
        output = child.communicate()[0]
    except OSError, e:
        print "UNKNOWN: check_jmx doesn't appear to be in the same path, grab it from https://github.com/tempspace/jmxquery"
        exit(3)
    transaction = dict([i.split('=') for i in output.split(' ') if '=' in i])
    try:
        transactions.append(int(transaction['LastCommittedTxId'].rstrip('\n')))
        status_string += host + ":" + transaction['LastCommittedTxId'].rstrip('\n') + " "
    except KeyError, e:
      print "UNKNOWN: Can't query JMX value from " + host
      exit(3)

if max(transactions) == min(transactions):
    print "OK: " + status_string
    exit(0)

# Assuming that the server with the highest committed transaction ID is the master
master = max(transactions)

for slave in transactions:
    delta = master - slave
    if delta >= int(cmd_options.critical):
        print "CRITICAL: " + status_string
        exit(2)
    if delta >= int(cmd_options.warn):
        print "WARN: " + status_string
        exit(1)

print "OK: " + status_string
exit(0)

