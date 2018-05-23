from abc import ABCMeta, abstractclassmethod
import subprocess
import re
import time
import pexpect
import csv
import logging
import os.path
logger1 = logging.getLogger("__main__")


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

    def run(self):

        result = list()

        #
        # Stage one
        #
        logger1.debug('Running external delay test for {0}'.format(self._description))

        try:
            result.append(ping_task(self._ext_ep))

        except Exception as e:
            result.append('ERROR')
            logger1.critical('Something went bad: {0}'.format(str(e)))
            # logger1.exception('Fatal issue while running the icmp test')

        #
        # Stage two
        #
        try:
            logger1.debug('Running vpn gw delay test for {0}'.format(self._description))
            before = time.perf_counter()

            startct = pexpect.spawn('startct -s ' + self._vpn_gw + ' -r ' + self._realm + ' -y', timeout=10)
            startct.expect('Username:')
            startct.sendline(self._username)

            startct.expect('Password:')
            startct.sendline(self._password)

            startct.expect('Enter')
            startct.sendline('1')
            startct.expect('CONNECT')

            startct.sendline('status')
            startct.expect('Connected')

            after = time.perf_counter()

            result.append(round((after - before) * 1000, 3))


        except Exception as e:
            result.append('ERROR')
            logger1.critical('Something went bad: {0}'.format(str(e)))
            #logger1.exception('Fatal issue while running the vpn test')

        #
        # Stage three
        #
        logger1.debug('Running internal delay test for {0}'.format(self._description))

        try:
            result.append(ping_task(self._int_ep))

        except Exception as e:
            result.append('ERROR')
            logger1.critical('Something went bad: {0}'.format(str(e)))
            #logger1.exception('Fatal issue while running the icmp test')

        #
        # Closing the vpn
        #

        try:
            startct.sendline('quit')

        except Exception as e:
            logger1.critical('Something went bad: {0}'.format(str(e)))
            #logger1.exception('Fatal issue while closing the vpn')

        return result


class ResultGen:
    def __init__(self, sites):
        self._sites = sites

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
            time.sleep(60 - (clock_after - clock_before))


class ResultLogger:
    def __init__(self, filename):
        self._date = time.strftime("%y%m%d", time.gmtime())
        self._filename = filename
        self._fieldnames = ['Time', 'CPE Name', 'Summary', 'Stage 1 in ms', 'Stage 2 in ms', 'Stage 3 in ms']
        self._alert = dict()

    def write_result(self, result_gen):

        for result in result_gen:
            logger1.debug('Stages results: {0}, {1}, {2}'.format(result['Stage 1 in ms'], result['Stage 2 in ms'], result['Stage 3 in ms']))

            # Every day a new result file needs to be created
            if time.strftime("%y%m%d", time.gmtime()) != self._date:
                self._date = time.strftime("%y%m%d", time.gmtime())
                logger1.warning('Rotating result file. New file: {0}'.format(self._filename))

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
                        logger1.warning('{0} consecutive failure for (1}. Sending emails'.format(self._alert['CPE Name'], result['CPE Name']))
                else:
                    self._alert[result['CPE Name']] = 1

            else:
                if result['CPE Name'] in self._alert.keys():
                    self._alert[result['CPE Name']] = 0




def main():

    sites = dict()

    logger1.warning('Loading configuration')

    with open('config.csv', 'r') as fd:
        csv_fd = csv.reader(fd,delimiter=',')
        for i, line in enumerate(csv_fd):
            if re.match('[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', line[1]) and \
                    re.match('[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', line[2]) and \
                    re.match('[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', line[3]):
                sites[line[0]] = {'external_ip': line[1]}
                sites[line[0]]['vpn_gw'] = line[2]
                sites[line[0]]['internal_ip'] = line[3]
                sites[line[0]]['username'] = line[4]
                sites[line[0]]['password'] = line[5]
                sites[line[0]]['realm'] = line[6]
            else:
                logger1.debug('Skipping line {0}'.format(i))

    if len(sites.keys()) > 0:
        logger1.warning('Start running tasks')
        ResultLogger('result').write_result(ResultGen(sites))

    else:
        logger1.critical('Empty configuration. Stopping')


if __name__ == '__main__':
    logger1.setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG, format='=%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='monitoring.log')
    main()