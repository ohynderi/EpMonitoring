# VPN GW Monitoring 
## Overview

The purpose of the EpMonitoring.py script is to monitor the availabilities of VPN Gateways using Sonicwall Connect Tunnel SSL VPN client.

The script relies on the Python pexpect module to launch ping or startx commands. Hence it requires a UNIX environnement to run.


## config.yml

The script takes its configuration from the config.yml file which needs to be in the same directory. 

That configuration file comes with 3 sections:

* logging: SMTP details to send an email when tests for a site has failed twice consecutively.
* sites: details of the sites to be tested.
* frequency: how often (in sec) are the tests run.

The sites section list the number of sites to be tests. Every <frequency>, sites are tested one after the other. 
Each site are tested as following:


## Error handling

