import subprocess
import re
import time
import logging
import pexpect
logger1 = logging.getLogger("__task__")

from abc import ABCMeta, abstractclassmethod

class Task(metaclass=ABCMeta):
    def __init__(self, site_id, description):
        self._site_id = site_id
        self._description = description

    @abstractclassmethod
    def run(self):
        pass

    @property
    def site_id(self):
        return self._site_id

    @property
    def description(self):
        return self._description


class Ping(Task):
    def __init__(self, ip_ep, site_id='', description=''):
        super().__init__(site_id, description)
        self._ip_ep = ip_ep

    def run(self):

        try:
            cmd_output = subprocess.run(["ping", self._ip_ep], stderr=subprocess.PIPE, stdout=subprocess.PIPE)

            if re.search('Average.*[0-9]+ms', cmd_output.stdout.decode('utf-8')):
                return re.search('Average.*[0-9]+', cmd_output.stdout.decode('utf-8')).group().split()[2]

            else:
                raise Exception('failed')

        except Exception as e:
            raise


class Vpn(Task):
    def __init__(self, vpn_gw, username='SSO-USR-MON', password='YP64W4p2', site_id='', description=''):
        super().__init__(site_id, description)
        self._vpn_gw = vpn_gw
        self._username = username
        self._password = password
        self._ip_ep = ip_ep

    def run(self):
        try:
            before = time.clock()

            startct = pexpect.spawn('startct -s ' + self._vpn_gw + ' -r nomad, timeout=10')
            startct.timeout = 10
            startct.expect('Username:')
            startct.sendline(self._username)

            startct.expect('Password:')
            startct.sendline(self._password)

            startct.expect('Enter')
            startct.sendline('1')
            startct.expect('CONNECT')

            startct.sendline('status')
            startct.expect('Connected')

            after = time.clock()

            yield after - before





            startct.sendline('quit')


            after = time.clock()
            return after - before

        except Exception as e:
            raise


class TaskGen:
    def __init__(self, sites):
        self.__sites = sites

    def __iter__(self):
        while True:
            for site in self.__sites.keys():

                result = dict()
                result['Time'] = time.asctime()
                result['CPE Name'] = site
                result['Result'] = 'SUCCESS'
                clock_before = time.clock()

                try:
                    logger1.debug('Running external delay test for {0}'.format(site))
                    result['Stage 1 in ms'] = Ping(self.__sites[site]['external_ip']).run()

                except Exception as e:
                    result['Stage 1 in ms'] = str(e)
                    result['Result'] = 'FAILURE'

                try:
                    logger1.debug('Running vpn gw delay test for {0}'.format(site))
                    result['Stage 2 in ms'] = Vpn(self.__sites[site]['external_ip'], self.__sites[site]['username'], self.__sites[site]['password']).run()

                except Exception as e:
                    result['Stage 2 in ms'] = str(e)
                    result['Result'] = 'FAILURE'

                try:
                    logger1.debug('Running internal delay test for {0}'.format(site))
                    result['Stage 3 in ms'] = Ping(self.__sites[site]['internal_ip']).run()


                except Exception as e:
                    result['Stage 3 in ms'] = str(e)
                    result['Result'] = 'FAILURE'


                yield result

                clock_after = time.clock()
                time.sleep(60 - (clock_after - clock_before))

