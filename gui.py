from hm_clock import HMClock
import sys
import platform
import datetime
import subprocess
import argparse
import logging
from pathlib import Path
import logzero
from logzero import logger
import pandas as pd

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout
from PyQt5.QtWidgets import QLabel, QPushButton, QGroupBox, QFileDialog, QLineEdit, QErrorMessage
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer

from widgets import VLine, ClockLabel, TimeEdit
from autoqr import AutoQR, open_csv
from scheduled_event import Periods
import utils
from config import settings

MSG_DURATION = 2000
logger.setLevel(logging.DEBUG)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.locker = utils.Locker()
        self.config_widgets = [
        ]  # widgets used for configuration. disabled during the execution
        self._init_widgets()
        self.df = pd.DataFrame()

    def _init_periods(self):
        period_group = QGroupBox('開始・終了時間')
        period_group.setLayout(QVBoxLayout())
        grid = QGridLayout()
        grid.addWidget(QLabel('開始', self), 0, 0, Qt.AlignCenter)
        grid.addWidget(QLabel('終了', self), 0, 1, Qt.AlignCenter)
        for i, period in enumerate(settings.PERIODS, start=1):
            start_time = TimeEdit()
            start_time.setText(period[0])
            start_time.setEnabled(False)
            grid.addWidget(start_time, i, 0, Qt.AlignCenter)
            stop_time = TimeEdit()
            stop_time.setText(period[1])
            stop_time.setEnabled(False)
            grid.addWidget(stop_time, i, 1, Qt.AlignCenter)
        period_group.layout().addLayout(grid)
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
        self.output_button = QPushButton('選択...')
        self.output_button.clicked.connect(on_browse_button_clicked)
        output_group.layout().addWidget(self.output_button)

        self.layout.addWidget(output_group)

    def _on_job_done(self):
        with self.locker.lock():
            self.log_label.setText('{} 完了. {:g} / h'.format(
                self.autoqr.done_count, self.autoqr.rate))
            if self.autoqr.done_count == len(self.df):
                logger.info('all jobs are finished')
                self.autoqr.finalize()
                logger.info('Finalization is over')
                self.statusBar().showMessage('全例終了')
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(False)
                for w in self.config_widgets:
                    w.setEnabled(True)

    def _init_input(self):
        def on_input_button_clicked():
            fileName, _ = QFileDialog.getOpenFileName(self, 'リストを開く', '',
                                                      'CSV File (*.csv)')
            if fileName == '':
                return

            logger.info('Open input:%s', fileName)
            try:
                self.df = open_csv(fileName)
            except Exception as e:
                logger.error(e)
                dialog = QErrorMessage(self)
                dialog.setWindowTitle('読み込みエラー')
                dialog.showMessage('無効なファイルです。{}'.format(str(e)))
                return
            logger.info('Done opening input:%s', fileName)
            self.statusBar().showMessage('リストの読み込み完了', MSG_DURATION)
            self.df['datetime'] = self.df[settings.COL_STUDY_DATE].map(
                lambda d: datetime.datetime.strptime(d, settings.
                                                     DATETIME_FORMAT))
            min_date, max_date = min(self.df['datetime']), max(
                self.df['datetime'])
            self.input_label.setText('ファイル名：{}、総数：{}\n期間：{} ~ {}'.format(
                Path(fileName).name, len(self.df),
                min_date.date().strftime('%Y/%m/%d'),
                max_date.date().strftime('%Y/%m/%d')))

            self.autoqr = AutoQR(self.output_edit.text(), logger)
            self.autoqr.add_job_done_handler(self._on_job_done)
            self.autoqr.set_df(self.df)
            self.output_button.setEnabled(False)
            self.update_button_state()

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

            self.autoqr.sched_event.start()

        def on_stop_button_clicked():
            logger.debug('stop button clicked')
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

            self.statusBar().showMessage('Pausing workers', MSG_DURATION)
            self.autoqr.sched_event.stop()

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
        self.periodLabel = QLabel()
        self.statusBar().addPermanentWidget(self.periodLabel)
        self.periods = Periods(settings.PERIODS)
        self.periodLabelTimer = QTimer(self)

        def update_period_label():
            in_time = self.periods.is_in(HMClock.now())
            if in_time:
                self.periodLabel.setText('実行時間内')
            else:
                self.periodLabel.setText('実行時間外')

        update_period_label()
        self.periodLabelTimer.timeout.connect(update_period_label)
        self.periodLabelTimer.start(1000)
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

            if len(self.df) == 0:
                return False

            return True

        if is_ready():
            self.start_button.setEnabled(True)


def main():
    parser = argparse.ArgumentParser(description='Auto Q/R.')
    parser.add_argument(
        '--logfile',
        help=
        "Log to the specified file. Specify '-' for no logfile. (Default:logs/%%y%%m%%d_%%H%%M%%S.log)",
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

    if args.logfile and args.logfile != '-':
        logzero.logfile(args.logfile, maxBytes=1e7, backupCount=256)
    else:
        logfile = Path('logs') / '{}.log'.format(
            datetime.datetime.today().strftime("%y%m%d_%H%M%S"))
        logfile.parent.mkdir(parents=True, exist_ok=True)
        logzero.logfile(logfile, maxBytes=1e7, backupCount=256)
        logger.info('Log filename:%s', str(logfile))
    logger.setLevel(args.loglevel)

    if len(settings.RECEIVE_PORTS) < settings.N_THREADS:
        print(settings.RECEIVE_PORTS)
        print('Invalid config. len(RECEIVE_PORTS) < N_THREADS ({} and {})'.
              format(len(settings.RECEIVE_PORTS), settings.N_THREADS))
        return 1

    if len(settings.AETS) < settings.N_THREADS:
        print(settings.AETS)
        print('Invalid config. len(AETS) < N_THREADS ({} and {})'.format(
            len(settings.AETS), settings.N_THREADS))
        return 1

    if len(settings.RECEIVE_PORTS) > settings.N_THREADS:
        logger.warning('N_THREADS < available ports (%s and %s)',
                       len(settings.RECEIVE_PORTS), settings.N_THREADS)

    logger.info('starting the application')

    window = MainWindow()
    window.show()
    app.exec_()

    return 0


if __name__ == '__main__':
    sys.exit(main())
