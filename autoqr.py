import datetime
import logging
from queue import Queue
import threading
from threading import Thread, Event
from pathlib import Path
from typing import Tuple
from logzero import logger as default_logger
import pandas as pd

from scheduled_event import ScheduledEvent
import qr
import utils
from config import settings

MSG_DURATION = 2000
default_logger.setLevel(logging.DEBUG)


class AutoQR():
    def __init__(self, outdir, logger):
        self.logger = logger
        self.sched_event = ScheduledEvent(settings.PERIODS, logger=self.logger)
        self.done_count = 0  # num of successes
        self.error_count = 0  # num of errors
        self.rate = 0
        self.locker = utils.Locker()
        self.t_deltas = []
        self.job_done_handlers = [self._on_job_done]
        self.error_handlers = [self._on_error]
        self.outdir = Path(outdir)
        header = [
            'StudyDate', 'OriginalPatientID', 'AnonymizedPatientID',
            'OriginalAccessionNumber', 'AnonymizedAccessionNumber',
            'OriginalStudyInstanceUID', 'AnonymizedStudyInstanceUID'
        ]
        self.anon_table = utils.CsvWriter(
            self.outdir /
            (datetime.datetime.today().strftime("%y%m%d_%H%M%S") + '.csv'),
            ','.join(header))
        self.error_filename = self.outdir / (
            datetime.datetime.today().strftime("%y%m%d_%H%M%S") +
            '_errors.txt')

        self.logger.info('Anon table filename:%s',
                         str(self.anon_table.filename))
        self.logger.info('Error log filename:%s', str(self.error_filename))
        self.threads = []
        self.task_queue = Queue()
        self.tid2conn_info = {}
        for i in range(settings.N_THREADS):
            t = Thread(target=self._worker,
                       args=(self._job, self.task_queue,
                             self.sched_event.event))
            t.setDaemon(True)
            self.threads.append(t)
            t.start()
            server = settings.DICOM_SERVERS[i % len(settings.AECS)]
            receive_port = settings.RECEIVE_PORTS[i]
            aet = settings.AETS[i]
            port = settings.PORTS[i % len(settings.PORTS)]
            aec = settings.AECS[i % len(settings.AECS)]
            info = qr.ConnectionInformation(server, aec, port, aet,
                                            receive_port)
            self.tid2conn_info[t.ident] = info

    def _worker(self, f, q: Queue, e: Event):
        while True:
            e.wait()
            args = q.get()
            f(*args)
            q.task_done()

    def _job(self, args: Tuple[str, str, str], tid2conn_info):
        start = datetime.datetime.now()
        PatientID, AccessionNumber, StudyInstanceUID = args
        self.logger.info('start retrieve and anonymize %s %s', PatientID,
                         StudyInstanceUID)
        try:
            ret = qr.qr_anonymize_save(PatientID,
                                       AccessionNumber,
                                       StudyInstanceUID,
                                       str(self.outdir),
                                       tid2conn_info[threading.get_ident()],
                                       predicate=qr.is_original_image,
                                       logger=self.logger)
        except Exception as e:
            self.logger.error('(%s,%s):%s', PatientID, StudyInstanceUID, e)
            self._handle_error(args, e)
            for handler in self.error_handlers:
                handler()
            return
        self._handle_result(args, ret, datetime.datetime.now() - start)
        self.logger.info('end retrieve %s %s', PatientID, StudyInstanceUID)
        for handler in self.job_done_handlers:
            handler()

    def _handle_result(self, args: Tuple[str, str, str],
                       ret: Tuple[str, str, str, str], t_delta):
        original_pid, original_an, original_suid = args
        new_pid, new_an, study_uid, study_date = ret
        newline = ','.join([
            str(e) for e in [
                study_date,
                original_pid,
                new_pid,
                original_an,
                new_an,
                original_suid,
                study_uid,
            ]
        ])
        with self.locker.lock():
            self.anon_table.add_line(newline)
            self.done_count += 1
            self.t_deltas.append(t_delta)
            mean_t_deltas = sum(self.t_deltas, datetime.timedelta()) / len(
                self.t_deltas)
            self.rate = 1 / (mean_t_deltas.total_seconds() /
                             3600) * settings.N_THREADS

    def _handle_error(self, args: Tuple[str, str, str], e):
        PatientID, _, StudyInstanceUID = args
        with self.locker.lock():
            self.error_count += 1
            with open(self.error_filename, 'a') as f:
                f.write('{},{},{}\n'.format(PatientID, StudyInstanceUID, e))

    def _on_job_done(self):
        if self.done_count + self.error_count == len(self.df):
            self.sched_event.stop()

    def _on_error(self):
        if self.done_count + self.error_count == len(self.df):
            self.sched_event.stop()

    def finalize(self):
        qr.shutdown()

    def add_job_done_handler(self, handler):
        self.job_done_handlers.append(handler)

    def add_error_handler(self, handler):
        self.error_handlers.append(handler)

    def set_df(self, df):
        self.df = df
        self.logger.info('Initialize task queue. (%d)', len(df))
        self.done_count = 0
        self.t_deltas = []
        self.task_queue.queue.clear()
        for pid, oid, suid in zip(self.df[settings.COL_PATIENT_ID],
                                  self.df[settings.COL_ACCESSION_NUMBER],
                                  self.df[settings.COL_STUDY_INSTANCE_UID]):
            self.task_queue.put([(pid, oid, suid), self.tid2conn_info])


def open_csv(filename):
    df = pd.read_csv(filename, encoding='cp932', dtype=str, na_filter=None)
    required_cols = [
        settings.COL_ACCESSION_NUMBER, settings.COL_STUDY_INSTANCE_UID,
        settings.COL_PATIENT_ID, settings.COL_STUDY_DATE
    ]
    for c in required_cols:
        if c not in df.columns:
            raise Exception('{}がありません。'.format(c))
    return df


def study_exists(basedir, year, date, pid, study_uid):
    outdir = qr.get_output_directory(basedir, year, date, pid, study_uid)
    files = list(outdir.glob('*.zip'))
    return len(files) > 0


def remove_existing(df: pd.DataFrame, basedir: Path):
    '''
    Args:
        df: Dataframe with "datetime" column.
    '''
    exists = df.apply(lambda row: study_exists(
        basedir, row.datetime.strftime('%Y'), row.datetime.strftime(
            '%m%d'), row.PatientID, row.StudyInstanceUID),
                      axis=1,
                      raw=False)
    return df[~exists]


def add_datetime(df: pd.DataFrame):
    '''
    Add datetime column.
    '''
    df['datetime'] = df[settings.COL_STUDY_DATE].map(
        lambda d: datetime.datetime.strptime(d, settings.DATETIME_FORMAT))
    return df
