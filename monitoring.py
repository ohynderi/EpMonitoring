from task import TaskGen
import time
import csv
import logging
import os.path
logger1 = logging.getLogger("__main__")



class ResultLogger:
    def __init__(self, filename):
        self._date = time.strftime("%y%m%d", time.gmtime())
        self._filename = filename
        self._fieldnames = ['Time', 'CPE Name', 'Result', 'Stage 1 in ms', 'Stage 2 in ms', 'Stage 3 in ms']

    def write_result(self, result_gen):

        for result in result_gen:
            logger1.debug(result)

            if time.strftime("%y%m%d", time.gmtime()) != self._date:
                self._date = time.strftime("%y%m%d", time.gmtime())
                logger1.warning('Rotating result file. New file: {0}'.format(self._filename))

                with open(self._filename + '_' + self._date + '.csv', 'a', newline='') as fd:
                    csv_write = csv.DictWriter(fd, fieldnames=self._fieldnames)
                    csv_write.writeheader()
                    csv_write.writerow(result)

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


def main():
    sites = dict()
    sites['nomad-eu.solvay.com'] = {'external_ip' : '150.251.5.80'}
    sites['nomad-eu.solvay.com']['username'] = ['']
    sites['nomad-eu.solvay.com']['password'] = ['']
    sites['nomad-eu.solvay.com']['internal_ip'] = ['1.1.1.1']

    sites['nomad-as.solvay.com'] = {'external_ip' : '101.231.53.22'}
    sites['nomad-as.solvay.com']['username'] = ['']
    sites['nomad-as.solvay.com']['password'] = ['']
    sites['nomad-as.solvay.com']['internal_ip'] = ['1.1.1.1']

    sites['nomad-eu.solvay.com'] = {'external_ip' : '150.251.5.80'}
    sites['nomad-eu.solvay.com']['username'] = ['']
    sites['nomad-eu.solvay.com']['password'] = ['']
    sites['nomad-eu.solvay.com']['internal_ip'] = ['1.1.1.1']

    logger1.warning('Start running tasks')
    ResultLogger('result').write_result(TaskGen(sites))

if __name__ == '__main__':
    logger1.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG, format='=%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main()