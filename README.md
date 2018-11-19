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

If, for a site, one step fails, site is considered as failedn (see the *Summary* column in the result file)

```
Time,CPE Name,Summary,Stage 1 in ms,Stage 2 in ms,Stage 3 in ms  
Wed Nov 14 05:18:02 2018,site1,FAILURE,5.002,ERROR,TIMEOUT
```

A notification is sent via email when a site has failed twice in a row.


## Script Logging

The scripts logs information into the monitoring.log file. By default, it logs up to the debug level. This can be lower by modifying following instruction:

```
logger1.setLevel(logging.DEBUG)
```


## Error handling
The script handles following two issues:
1. It was noticed that the SSL client doesnt always close properly. 
When this happens, the processes started by the startct commands keep running, preventing any new connection and hence subsequent tests to fail… 
To work around this, prior testing a site, the script checks if the SSL client is still running and kill if it does.
2. It was noticed that after closing the SSL client, the DNS setting (/etc/resolv.conf file) are not always restored to default causing subsequent tests to fail. 
To work around this, before testing a site, the script checks the content of the /etc/resolv.conf. If still modified by the previous execution of the startct command, it runs the “resolvconf –u” command. This requires that “sudo resolvconf –u” can be run without being asked for password.
