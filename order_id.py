import sys
import platform
import datetime
import time
import subprocess
import argparse
import logging
from queue import Queue
from threading import Thread, Event, Lock
from pathlib import Path
from typing import Tuple
import logzero
from logzero import logger
import pandas as pd

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QLabel, QPushButton, QGroupBox, QFileDialog, QLineEdit, QCheckBox, QErrorMessage
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer

from widgets import VLine, ClockLabel, TimeEdit
from hm_clock import HMClock
import qr
from config import settings

MSG_DURATION = 2000

logger.setLevel(logging.DEBUG)


def job(args: Tuple[str, str, str], return_handler, error_handler):
    start = datetime.datetime.now()
    PatientID, AccessionNumber, outdir = args
    logger.info('start retrieve and anonymize %s %s', PatientID,
                AccessionNumber)
    try:
        ret = qr.qr_anonymize_save(PatientID,
                                   AccessionNumber,
                                   outdir,
                                   predicate=qr.is_original_image,
                                   logger=logger)
    except Exception as e:
        logger.error('%s', e)
        error_handler(args, e)
        return
    return_handler(args, ret, datetime.datetime.now() - start)
    logger.info('end retrieve %s %s', PatientID, AccessionNumber)


def worker(f, q: Queue, e: Event):
    while True:
        e.wait()
        args = q.get()
        f(*args)
        q.task_done()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.df = None
        self.start_timer = QTimer(self)
        self.start_timer.setSingleShot(True)
        self.start_timer.timeout.connect(self.start_workers)
        self.stop_timer = QTimer(self)
        self.stop_timer.setSingleShot(True)
        self.stop_timer.timeout.connect(self.stop_workers_w_start_timer)
        self.task_queue = Queue()
        self.table_filename = 'table.csv'
        self.error_filename = 'errors.txt'
        self.done_count = 0
        self.t_deltas = []
        self.config_widgets = [
        ]  # widgets used for configuration. disabled during the execution
        self._init_widgets()

        self.event = Event()
        self.event.clear()
        self.thread = Thread(target=worker,
                             args=(job, self.task_queue, self.event))
        self.thread.setDaemon(True)
        self.thread.start()

    def is_in_time(self):
        start = HMClock.from_str(self.start_time.text())
        stop = HMClock.from_str(self.stop_time.text())
        now = HMClock.now()

        return now.is_between(start, stop)

    def _init_periods(self):
        period_group = QGroupBox('開始・終了時間')
        period_group.setLayout(QVBoxLayout())
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel('開始', self))
        self.start_time = TimeEdit()
        self.start_time.setText(settings.START_TIME)
        self.config_widgets.append(self.start_time)
        top_layout.addWidget(self.start_time)
        top_layout.addWidget(QLabel('終了', self))
        self.stop_time = TimeEdit()
        self.stop_time.setText(settings.STOP_TIME)
        self.config_widgets.append(self.stop_time)
        top_layout.addWidget(self.stop_time)
        period_group.layout().addLayout(top_layout)

        self.ignore_weekend = QCheckBox('土日は止めない')
        self.ignore_weekend.setChecked(True)
        self.config_widgets.append(self.ignore_weekend)
        period_group.layout().addWidget(self.ignore_weekend)

        self.layout.addWidget(period_group)

    def _init_output(self):
        def on_browse_button_clicked():
            fileName = QFileDialog.getExistingDirectory(self, '出力先フォルダを選択')
            if fileName != '':
                self.output_edit.setText(fileName)
                logger.info('Set output directory:%s', fileName)
                self.update_button_state()

        output_group = QGroupBox('出力フォルダ')
        output_group.setLayout(QHBoxLayout())
        self.output_edit = QLineEdit()
        self.output_edit.setEnabled(False)
        self.output_edit.setText(
            str(Path.home() / 'Desktop' /
                datetime.date.today().strftime('%m%d')))
        output_group.layout().addWidget(self.output_edit)
        output_button = QPushButton('選択...')
        output_button.clicked.connect(on_browse_button_clicked)
        self.config_widgets.append(output_button)
        output_group.layout().addWidget(output_button)

        self.layout.addWidget(output_group)

    def _handle_result(self, args: Tuple[str, str], ret: Tuple[str, str, str,
                                                               str], t_delta):
        original_pid, original_an, _ = args
        new_pid, new_an, study_uid, study_date = ret
        with open(self.table_filename, 'a') as f:
            f.write(','.join([
                str(e) for e in [
                    study_date,
                    original_pid,
                    new_pid,
                    original_an,
                    new_an,
                    study_uid,
                ]
            ]))
            f.write('\n')
        self.done_count += 1
        self.t_deltas.append(t_delta)
        mean_t_deltas = sum(self.t_deltas, datetime.timedelta()) / len(
            self.t_deltas)
        rate = 1 / (mean_t_deltas.total_seconds() / 3600)
        self.log_label.setText('{} 完了. {:g} / h'.format(self.done_count, rate))
        if self.done_count == len(self.df):
            logger.info('all jobs are finished')
            self.statusBar().showMessage('全例終了')
            self.stop_workers()
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            for w in self.config_widgets:
                w.setEnabled(True)

    def _handle_error(self, args: Tuple[str, str], e):
        PatientID, AccessionNumber = args
        with open(self.error_filename, 'a') as f:
            f.write('{} {} {}\n'.format(PatientID, AccessionNumber, e))
        self.done_count += 1

    def _init_input(self):
        def on_input_button_clicked():
            fileName, _ = QFileDialog.getOpenFileName(self, 'リストを開く', '',
                                                      'CSV File (*.csv)')
            if fileName == '':
                return

            try:
                logger.info('Open input:%s', fileName)
                self.df = pd.read_csv(fileName, encoding='cp932', dtype=str)
                required_cols = [
                    settings.COL_ACCESSION_NUMBER, settings.COL_PATIENT_ID,
                    settings.COL_STUDY_DATE
                ]
                for c in required_cols:
                    if c not in self.df.columns:
                        raise Exception('{}がありません。'.format(c))
                self.df['datetime'] = self.df[settings.COL_STUDY_DATE].map(
                    lambda d: datetime.datetime.strptime(
                        d, settings.DATETIME_FORMAT))
                min_date, max_date = min(self.df['datetime']), max(
                    self.df['datetime'])
                self.input_label.setText('ファイル名：{}、総数：{}\n期間：{} ~ {}'.format(
                    Path(fileName).name, len(self.df),
                    min_date.date().strftime('%Y/%m/%d'),
                    max_date.date().strftime('%Y/%m/%d')))

                self.done_count = 0
                self.t_deltas = []
                self.task_queue.queue.clear()
                for pid, oid in zip(self.df[settings.COL_PATIENT_ID],
                                    self.df[settings.COL_ACCESSION_NUMBER]):
                    self.task_queue.put([(pid, oid, self.output_edit.text()),
                                         self._handle_result,
                                         self._handle_error])
                self.update_button_state()
            except Exception as e:
                logger.error(e)
                dialog = QErrorMessage(self)
                dialog.setWindowTitle('読み込みエラー')
                dialog.showMessage('無効なファイルです。{}'.format(str(e)))

            self.statusBar().showMessage('リストの読み込み完了')

        input_group = QGroupBox('患者リスト')
        input_group.setLayout(QVBoxLayout())
        input_button = QPushButton('リストを開く')
        input_button.clicked.connect(on_input_button_clicked)
        self.config_widgets.append(input_button)
        input_group.layout().addWidget(input_button)
        self.input_label = QLabel('リストがありません', self)
        self.input_label.setAlignment(Qt.AlignCenter)
        input_group.layout().addWidget(self.input_label)

        self.layout.addWidget(input_group)

    def _init_status(self):
        group = QGroupBox('経過')
        group.setLayout(QHBoxLayout())

        self.log_label = QLabel('0 完了')
        self.log_label.setAlignment(Qt.AlignCenter)
        group.layout().addWidget(self.log_label)
        self.layout.addWidget(group)

    def start_workers(self):
        logger.debug('start_workers')
        self.statusBar().showMessage('Starting workers', MSG_DURATION)
        stop = HMClock.from_str(self.stop_time.text())
        clock_delta = stop - HMClock.now()
        stop_time = datetime.datetime.now() + datetime.timedelta(
            minutes=clock_delta.to_minute())
        if self.ignore_weekend.isChecked():
            while stop_time.weekday() in [5, 6]:
                logger.info('Skip weekend %s', stop_time)
                stop_time = stop_time + datetime.timedelta(days=1)

        wait = stop_time - datetime.datetime.now()
        self.stop_timer.start(wait.total_seconds() * 1000)
        logger.info('Scheduling stop in %dh %dm at %s',
                    wait.days * 24 + (wait.seconds // 3600),
                    (wait.seconds % 3600) // 60, stop_time)
        self.event.set()

    def set_start_timer(self):
        start = HMClock.from_str(self.start_time.text())
        wait = start - HMClock.now()
        self.start_timer.start(wait.to_msec() -
                               datetime.datetime.now().second * 1000)
        logger.info('Scheduling start in %dh %dm at %s', wait.hour,
                    wait.minute, start)
        self.statusBar().showMessage('Scheduled to start at {}'.format(
            HMClock.from_str(self.start_time.text())))

    def stop_workers(self):
        logger.info('stop_workers')
        self.event.clear()

    def stop_workers_w_start_timer(self):
        logger.info('stop_workers_w_start_timer')
        self.set_start_timer()
        self.event.clear()

    def _init_buttons(self):
        self.stop_button = QPushButton('Pause')
        self.stop_button.setEnabled(False)
        self.start_button = QPushButton('Start')
        self.start_button.setEnabled(False)

        def on_start_button_clicked():
            logger.debug('start button clicked')
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            for w in self.config_widgets:
                w.setEnabled(False)

            output_dir = Path(self.output_edit.text())
            output_dir.mkdir(parents=True, exist_ok=True)
            self.table_filename = output_dir / (
                datetime.datetime.today().strftime("%y%m%d_%H%M%S") + '.csv')
            with open(self.table_filename, 'w') as f:
                f.write(
                    'StudyDate,OriginalPatientID,AnonymizedPatientID,OriginalAccessionNumber,AnonymizedAccessionNumber,AnonymizedStudyInstanceUID\n'
                )
            self.error_filename = output_dir / (
                datetime.datetime.today().strftime("%y%m%d_%H%M%S") +
                '_errors.txt')

            if self.is_in_time():
                self.start_workers()
            else:
                self.set_start_timer()

        def on_stop_button_clicked():
            logger.debug('stop button clicked')
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

            self.statusBar().showMessage('Pausing workers', MSG_DURATION)
            self.start_timer.stop()
            self.stop_timer.stop()
            self.stop_workers()

        self.stop_button.clicked.connect(on_stop_button_clicked)
        self.start_button.clicked.connect(on_start_button_clicked)

        self.layout.addStretch()

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.stop_button)
        bottom_layout.addWidget(self.start_button)

        self.layout.addLayout(bottom_layout)

    def _init_widgets(self):
        central = QWidget(self)
        self.layout = QVBoxLayout()
        central.setLayout(self.layout)
        self.setCentralWidget(central)
        self.setWindowTitle('Auto Q/R')
        self.setMinimumSize(512, 512)

        self.statusBar().setStyleSheet(
            'color: black;background-color: #FFF8DC;')
        self.statusBar().showMessage('App started.', MSG_DURATION)
        self.statusBar().addPermanentWidget(VLine())
        self.statusBar().addPermanentWidget(ClockLabel(self))

        self._init_periods()
        self._init_output()
        self._init_input()
        self._init_status()
        self._init_buttons()

    def update_button_state(self):
        def is_ready():
            if self.output_edit.text() == '':
                return False

            if self.df is None:
                return False

            return True

        if is_ready():
            self.start_button.setEnabled(True)


def main():
    parser = argparse.ArgumentParser(description='Auto Q/R.')
    parser.add_argument('--logfile',
                        help="Log to the specified file",
                        metavar='<filename>')

    parser.add_argument(
        '--loglevel',
        help="Loglevel. default:%(default)s. choices:[%(choices)s]",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='DEBUG',
        metavar='<str>')

    args = parser.parse_args()

    app = QApplication([])
    app.setStyle('Fusion')

    if platform.system() == 'Windows':
        font = QFont("Courier New", pointSize=10)
        font.setStyleHint(QFont.Monospace)
        app.setFont(font)

    if platform.system() == 'Darwin':
        font = QFont("Osaka", pointSize=12)
        font.setStyleHint(QFont.Monospace)
        app.setFont(font)

    try:
        subprocess.check_call(
            [str(Path(settings.DCMTK_BINDIR) / 'movescu'), '-h'],
            stdout=subprocess.DEVNULL)
    except Exception as e:
        logger.error(e)
        dialog = QErrorMessage()
        dialog.setWindowTitle('dcmtk エラー')
        dialog.showMessage(str(e))
        app.exec_()
        return 1

    if args.logfile:
        logzero.logfile(args.logfile, maxBytes=1e7, backupCount=3)
    logger.setLevel(args.loglevel)

    logger.info('starting the application')

    window = MainWindow()
    window.show()
    app.exec_()

    return 0


if __name__ == '__main__':
    sys.exit(main())
