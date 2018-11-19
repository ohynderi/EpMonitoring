# VPN GW Monitoring 
## Overview

The purpose of the EpMonitoring.py script is to monitor the availabilities of VPN Gateways using the Sonicwall Connect Tunnel SSL VPN client in CLI mode.

The script relies on the Python pexpect module to launch ping or startct commands. Hence it must run in a UNIX environment and require the Sonicwall Connect Tunnel client to be pre-installed.



## config.yml

The script takes its configuration from the config.yml file (YaML format) which needs to be in the same directory. 

The configuration file comes with 3 sections:

* logging: SMTP details for email notifications
* sites: details of the sites (hosting the VPN Concentrators) to be monitored.
* frequency: how often (in sec) are sites monitored

See file example_config.yml for more details.


## Site Monitoring

The sites section lists the sites to be monitored. 
At every <frequency>, the script tests all the sites, one after the other. So the time required to test all sites should be less than the frequency…
  
Each site are tested as following:
1. Ping the external ip resource (external_ip), avg RTT taken as result.
2. Setup an SSL connection to the site VPN GW, time to login taken as a result
3. Ping the internal ip resource (internal_ip), avg RTT taken as result.

It is recommended not to perform any type of host integrity / compliancy checking for the test user.


## Result 

Site results are stored in below format into a CSV file, located in the result directory. 
Result are being rotated every days. So one result file per day.

```
Time,CPE Name,Summary,Stage 1 in ms,Stage 2 in ms,Stage 3 in ms  
Wed Nov 14 00:03:40 2018,site1,SUCCESS,5.213,10529.671,436.733  
Wed Nov 14 00:03:40 2018,site2,SUCCESS,5.213,10529.671,436.733  
Wed Nov 14 00:03:59 2018,site3,SUCCESS,4.918,5518.176,148.335  
Wed Nov 14 00:04:13 2018,site1,SUCCESS,4.963,3339.573,16.167  
Wed Nov 14 00:14:25 2018,site2,SUCCESS,4.989,10519.918,446.857 
...
```

Stage 1-3 corresponding to step 1-3 in the *Site Montoring* section.

If, for a site, one step fails, site is considered as failed (see the *Summary* column in the result file)

```
Time,CPE Name,Summary,Stage 1 in ms,Stage 2 in ms,Stage 3 in ms  
Wed Nov 14 05:18:02 2018,site1,FAILURE,5.002,ERROR,TIMEOUT
```

A notification is sent via email when a site fails twice in a row.


## Script Logging

The scripts logs information into the monitoring.log file. By default, it logs up to the debug level. This can be lower by modifying following instruction:

```
logger1.setLevel(logging.DEBUG)
```

Depending on the logging level configured, the script logs information such as:
* Details on the test failure (in case of pexpect error)
* Additional results (avg/max/mdev) for the ping tests
* When the result file is being rotated 
* When the tests are started
* …

See below an example of what is being logged when stage 2 timesout 
```
=2018-11-14 05:18:06,378 - __main__ - DEBUG - Running vpn gw delay test for site2
=2018-11-14 05:18:40,706 - __main__ - CRITICAL - Something went bad when connecting: Timeout exceeded.
<pexpect.pty_spawn.spawn object at 0x7f530ae993c8>
command: /usr/bin/startct
args: ['/usr/bin/startct', '-s', 'site1.domain1.com', '-r', 'domain1', '-y', '60']
buffer (last 100 chars): b' your choice [1]: 1\r\n'
before (last 100 chars): b' your choice [1]: 1\r\n'
after: <class 'pexpect.exceptions.TIMEOUT'>
match: None
match_index: None
exitstatus: None
flag_eof: False
pid: 52873
child_fd: 6
closed: False
timeout: 30
delimiter: <class 'pexpect.exceptions.EOF'>
logfile: None
logfile_read: None
logfile_send: None
maxread: 2000
ignorecase: False
searchwindowsize: None
delaybeforesend: 0.05
delayafterclose: 0.1
delayafterterminate: 0.1
searcher: searcher_re:
    0: re.compile(b'CONNECT')
=2018-11-14 05:18:40,707 - __main__ - DEBUG - Running internal delay test for nomad-as
=2018-11-14 05:18:55,263 - __main__ - DEBUG - Stages results: 5.002, ERROR, TIMEOUT
```

The logging file rotates automatically after reaching 5MB. Up to 10 files are kept.


## Error handling
The script handles following two issues:
1. It was noticed that the SSL client doesnt always close properly. 
When this happens, the processes started by the startct commands keep running, preventing any new connection and hence subsequent tests to fail… 
To work around this, prior testing a site, the script checks if the SSL client is still running and kill when it does. When this happens, following is being logged

```
=2018-11-14 05:18:59,316 - __main__ - CRITICAL - Ps java with pid 52877 was found to be running...
=2018-11-14 05:18:59,317 - __main__ - CRITICAL - Ps AvConnect with pid 52909 was found to be running...
=2018-11-14 05:18:59,319 - __main__ - CRITICAL - Killing Ps AvConnect with pid 52909
=2018-11-14 05:19:00,326 - __main__ - CRITICAL - Killing Ps java with pid 52877
```

2. It was noticed that after closing the SSL client, the DNS setting (/etc/resolv.conf file) are not always restored to default causing subsequent tests to fail. 
To work around this, before testing a site, the script checks the content of the /etc/resolv.conf. If still modified by the previous execution of the startct command, it runs the “resolvconf –u” command. This requires that “sudo resolvconf –u” can be run without being asked for password.
