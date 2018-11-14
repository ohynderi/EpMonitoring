# VPN GW Monitoring 
## Overview

The purpose of the EpMonitoring.py script is to monitor the availabilities of VPN Gateways using the Sonicwall Connect Tunnel SSL VPN client.

The script relies on the Python pexpect module to launch ping or startct commands. Hence it must run in a UNIX environment to run.


## config.yml

The script takes its configuration from the config.yml file (YaML format) which needs to be in the same directory. 

The configuration file comes with 3 sections:

* logging: SMTP details to email notifications
* sites: details of the sites (hosting the VPN Concentrators) to be tested.
* frequency: how often (in sec) do we test the sites

## Site Monitoring

The sites section lists the sites to be tested. At every <frequency>, the script tests all the sites, one after the other. So the time required to test all sites should be less than the frequency…
Each site are tested as following:
1. Ping the external ip resource (external_ip), avg RTT taken as result.
2. Setup an SSL connection to the site VPN GW, time to login taken as a result
3. Ping the internal ip resource (internal_ip), avg RTT taken as result.
4. Tear down the SSL connection.

## Result 

Site results are store in a result CSV file that rotates every days. So every day a new result file is created.
If, for a site, one step failed, the site is considered as failed. If a site has been marked as failed twice in a row, a notification is sent via email.

## Error handling
The script handles following two issues:
1. It was noticed that the SSL client doesnt always close properly. 
When this happens, the processes started by the startct commands keep running, preventing any new connection and hence subsequent tests to fail… 
To work around this, prior testing a site, the script checks if the SSL client is still running and kill if it does.
2. It was noticed that after closing the SSL client, the DNS setting (/etc/resolv.conf file) are not always restored to default causing subsequent tests to fail. 
To work around this, before testing a site, the script checks the content of the /etc/resolv.conf. If still modified by the previous execution of the startct command, it runs the “resolvconf –u” command. This requires that “sudo resolvconf –u” can be run without being asked for password.
