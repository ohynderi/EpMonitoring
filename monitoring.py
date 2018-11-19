from abc import ABCMeta, abstractclassmethod
import subprocess
import re
import time
import pexpect
import csv
import logging
import logging.handlers
import os.path
import os
import yaml
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import psutil


def ping_task(ip_ep):
    cmd_output = subprocess.run(["ping", ip_ep, "-c", "5"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    if re.search('avg.*', cmd_output.stdout.decode('utf-8')):
        logger1.debug(re.search('avg.*', cmd_output.stdout.decode('utf-8')).group())
        return re.search('avg.*', cmd_output.stdout.decode('utf-8')).group().split('=')[1].split('/')[1]

    else:
        return 'TIMEOUT'


class Scenario(metaclass=ABCMeta):
    def __init__(self, description=''):
        self._description = description

    @abstractclassmethod
    def run(self):
        pass


class PingScenario(Scenario):
    def __init__(self, description, ip_ep):
        super().__init__(description)
        self._ip_ep = ip_ep

    def run(self):
        try:
            return ping_task(self._ip_ep)

        except Exception as e:
            logger1.critical('Something went bad: {0}'.format(str(e)))
            logger1.exception('Fatal issue while running the icmp test')
            return 'ERROR'


class VpnScenario(Scenario):
    def __init__(self, description, arg_dict):
        super().__init__(description)
        self._ext_ep = arg_dict['external_ip']
        self._vpn_gw = arg_dict['vpn_gw']
        self._int_ep = arg_dict['internal_ip']
        self._username = arg_dict['username']
        self._password = arg_dict['password']
        self._realm = arg_dict['realm']
        self._timeout = str(arg_dict['timeout'])


    def _check_proc_running(self):

        #
        # Check if startct is not running yet
        #

        pids = psutil.pids()
        startct = None
        AvConnect = None
        java = None

        try:
            for pid in pids:
                if psutil.Process(pid).name() == 'startct':
                    startct = pid
                    logger1.critical('Ps startct with pid {0} was found to be running...'.format(pid))

                if psutil.Process(pid).name() == 'java':
                    java = pid
                    logger1.critical('Ps java with pid {0} was found to be running...'.format(pid))

                if psutil.Process(pid).name() == 'AvConnect':
                    AvConnect = pid
                    logger1.critical('Ps AvConnect with pid {0} was found to be running...'.format(pid))

        except Exception as e:
            logger1.critical('Something went bad when reading process details: {0}'.format(str(e)))


        try:
            if startct and psutil.pid_exists(startct):
                logger1.critical('Killing Ps startct with pid {0}'.format(startct))
                psutil.Process(startct).kill()
                time.sleep(1)

            if AvConnect and psutil.pid_exists(AvConnect):
                logger1.critical('Killing Ps AvConnect with pid {0}'.format(AvConnect))
                psutil.Process(AvConnect).kill()
                time.sleep(1)

            if java and psutil.pid_exists(java):
                logger1.critical('Killing Ps java with pid {0}'.format(java))
                psutil.Process(java).kill()
                time.sleep(1)

        except Exception as e:
            logger1.critical('Something went bad when killing a process: {0}'.format(str(e)))


        # Give time time to the system and the vpn gw for killing / closing the ssl connection...
        if startct or AvConnect or java:
            time.sleep(10)


    def _check_dns(self):

        try:
            with open('/etc/resolv.conf', 'r') as fd:
                for line in fd:
                    if re.search('SonicWall', line):
                        logger1.critical('Invalid DNS settings. Forcing refresh')

                        '''
                        This script assumes 'resolvconf' can be run without being asked for password.
                        Hence, make sure to add 'sslvpn  ALL=(ALL) NOPASSWD: /sbin/resolvconf' to /etc/sudoers
                        '''

                        os.system('sudo resolvconf -u')
                        time.sleep(10)
                        break

        except Exception as e:
            logger1.critical('Something went bad when checking the dns settings: {0}'.format(str(e)))


    def run(self):

        startct = None
        result = list()

        #
        # Stage one
        # Ping the external ip
        #
        logger1.debug('Running external delay test for {0}'.format(self._description))

        try:
            result.append(ping_task(self._ext_ep))

        except Exception as e:
            result.append('ERROR')
            logger1.critical('Something went bad when writing the results: {0}'.format(str(e)))


        #
        # Stage two
        # Setting up the vpn
        #
        self._check_proc_running()
        self._check_dns()

        try:
            logger1.debug('Running vpn gw delay test for {0}'.format(self._description))
            before = time.perf_counter()

            startct = pexpect.spawn('startct -s ' + self._vpn_gw + ' -r ' + self._realm + ' -y ' + self._timeout)
            startct.expect('Username:')
            startct.sendline(self._username)

            startct.expect('Password:')
            startct.sendline(self._password)

            startct.expect('Enter')
            startct.sendline('1')
            startct.expect('CONNECT')

            # startct.sendline('status')
            # startct.expect('Connected')

            after = time.perf_counter()
            result.append(round((after - before) * 1000, 3))


        except Exception as e:
            result.append('ERROR')
            logger1.critical('Something went bad when connecting: {0}'.format(str(e)))

        #
        # Stage three
        # Pinging the external ip
        #
        logger1.debug('Running internal delay test for {0}'.format(self._description))

        try:
            result.append(ping_task(self._int_ep))

        except Exception as e:
            result.append('ERROR')
            logger1.critical('Something went bad: {0}'.format(str(e)))

        #
        # Closing the vpn
        #

        try:
            startct.sendline('quit')

        except Exception as e:
            logger1.critical('Something went bad when closing the vpn: {0}'.format(str(e)))

        return result


class ResultGen:
    def __init__(self, sites, sleep_time = 600):
        self._sites = sites
        self._sleep_time = sleep_time

    def __iter__(self):
        while True:

            clock_before = time.clock()

            for site in self._sites.keys():

                result = dict()
                result['Time'] = time.asctime()
                result['CPE Name'] = site
                result['Summary'] = 'SUCCESS'
                clock_before = time.clock()

                for i, delay in enumerate(VpnScenario(site, self._sites[site]).run()):
                    result['Stage ' + str(i+1) + ' in ms'] = delay

                    if not re.match('[0-9\.]+', str(delay)):
                        result['Summary'] = "FAILURE"

                yield result


            clock_after = time.clock()

            if self._sleep_time - (clock_after - clock_before) > 0:
                time.sleep(self._sleep_time - (clock_after - clock_before))


class ResultLogger:
    def __init__(self, config):
        self._date = time.strftime("%y%m%d", time.gmtime())
        self._filename = config['dir'] + '/' + config['file']
        self._email = config['email']
        self._fieldnames = ['Time', 'CPE Name', 'Summary', 'Stage 1 in ms', 'Stage 2 in ms', 'Stage 3 in ms']
        self._alert = dict()

    def _send_email(self, subject):
        msg = MIMEMultipart()
        msg['From'] = self._email['from']
        msg['To'] = self._email['to']
        msg['Subject'] = subject

        try:
            mail_server = smtplib.SMTP(self._email['server'] + ':25', timeout=10)
            mail_server.set_debuglevel(1)
            retcode = mail_server.ehlo()
            logger1.warning(retcode)
            retcode = mail_server.sendmail(self._email['from'], self._email['to'], msg.as_string())
            logger1.warning(retcode)
            mail_server.quit()

        except Exception as e:
            logger1.critical('Something went bad when sending an email: {0}'.format(str(e)))


    def write_result(self, result_gen):

        for result in result_gen:
            logger1.debug('Stages results: {0}, {1}, {2}'.format(result['Stage 1 in ms'], result['Stage 2 in ms'], result['Stage 3 in ms']))

            # Every day a new result file needs to be created
            if time.strftime("%y%m%d", time.gmtime()) != self._date:
                self._date = time.strftime("%y%m%d", time.gmtime())
                logger1.warning('Rotating result file. New file: {0}'.format(self._filename + '_' + self._date + '.csv'))

                with open(self._filename + '_' + self._date + '.csv', 'a', newline='') as fd:
                    csv_write = csv.DictWriter(fd, fieldnames=self._fieldnames)
                    csv_write.writeheader()
                    csv_write.writerow(result)

            # If result file doesnt exit, it needs to be created with header
            if not os.path.isfile(self._filename + '_' + self._date + '.csv',):
                logger1.warning('Creating result file {0}'.format(self._filename + '_' + self._date + '.csv'))

                with open(self._filename + '_' + self._date + '.csv', 'a', newline='') as fd:
                    csv_write = csv.DictWriter(fd, fieldnames=self._fieldnames)
                    csv_write.writeheader()
                    csv_write.writerow(result)

            else:
                with open(self._filename + '_' + self._date + '.csv', 'a', newline='') as fd:
                    csv_write = csv.DictWriter(fd, fieldnames=self._fieldnames)
                    csv_write.writerow(result)

            # Sending an email if two consecutive failures for a site
            if result['Summary'] != 'SUCCESS':
                if result['CPE Name'] in self._alert.keys():
                    self._alert[result['CPE Name']] += 1
                    if self._alert[result['CPE Name']] >= 2:
                        logger1.warning('{0} consecutive failure for {1}. Sending emails'.format(self._alert[result['CPE Name']], result['CPE Name']))
                        self._send_email('{0} consecutive failure for {1}.'.format(self._alert[result['CPE Name']], result['CPE Name']))

                else:
                    self._alert[result['CPE Name']] = 1

            else:
                if result['CPE Name'] in self._alert.keys():
                    self._alert[result['CPE Name']] = 0


def main():

    with open('config.yml', 'r') as yaml_file:
        logger1.debug('Loading configuration')
        config = yaml.load(yaml_file)
        logger1.debug('Configuration loaded')

    if len(config['sites'].keys()) > 0:
        logger1.warning('Start running tasks')
        ResultLogger(config['logging']).write_result(ResultGen(config['sites'], config['frequency']))

    else:
        logger1.critical('Empty configuration. Stopping')


if __name__ == '__main__':
    logger1 = logging.getLogger("__main__")

    logger1.setLevel(logging.DEBUG)
    log_formatter1 = logging.Formatter('=%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler1 = logging.handlers.RotatingFileHandler('monitoring.log', maxBytes=5000000, backupCount=10)
    log_handler1.setFormatter(log_formatter1)
    logger1.addHandler(log_handler1)

    #logging.basicConfig(level=logging.WARNING, format='=%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='monitoring.log')


    main()