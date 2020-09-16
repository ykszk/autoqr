import os
import datetime
from pathlib import Path
from logzero import logger
from queue import Queue
from threading import Thread, Event
import time
import pandas as pd

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QLabel, QPushButton, QRadioButton, QGroupBox, QFileDialog, QLineEdit, QErrorMessage, QTextEdit
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from widgets import ClockLabel, TimeEdit

app = QApplication([])
app.setStyle('Fusion')

if os.name == 'nt':
    font = QFont("Courier New", pointSize=10)
    font.setStyleHint(QFont.Monospace)
    app.setFont(font)

MSG_DURATION = 2000
N_THREADS = 2


def worker(q: Queue, e: Event):
    while True:
        e.wait()
        result = q.get()
        time.sleep(1)
        logger.info(result)
        q.task_done()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.df = None
        self.threads = []
        self.events = []
        self.task_queue = Queue()
        self.config_widgets = [
        ]  # widgets used for configuration. disabled during the execution
        self.init_widgets()

        for _ in range(N_THREADS):
            e = Event()
            e.clear()
            self.events.append(e)
            t = Thread(target=worker, args=(self.task_queue, e))
            t.setDaemon(True)
            self.threads.append(t)
            t.start()

    def init_widgets(self):
        central = QWidget(self)
        self.setWindowTitle('Auto Q/R')
        self.setMinimumSize(512, 512)

        self.stop_button = QPushButton('Stop')
        self.stop_button.setEnabled(False)
        self.start_button = QPushButton('Start')
        self.start_button.setEnabled(False)

        def on_start_button_clicked():
            logger.info('start button clicked')
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            for w in self.config_widgets:
                w.setEnabled(False)

            for e in self.events:
                e.set()

        def on_stop_button_clicked():
            logger.info('stop button clicked')
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            for w in self.config_widgets:
                w.setEnabled(True)

            for e in self.events:
                e.clear()

        def on_browse_button_clicked():
            fileName = QFileDialog.getExistingDirectory(self, r'出力先フォルダを選択')
            if fileName != '':
                self.output_edit.setText(fileName)
                logger.info('Set output directory:{}'.format(fileName))
                self.update_button_state()

        def on_input_button_clicked():
            fileName, _ = QFileDialog.getOpenFileName(self, r'リストを開く', '',
                                                      'CSV File (*.csv)')
            if fileName != '':
                try:
                    logger.info('Open input:{}'.format(fileName))
                    self.df = pd.read_csv(fileName, encoding='cp932')
                    required_cols = [
                        r'オーダー番号', r'受診者ID', r'検査日(yyyy/MM/dd HH:mm)'
                    ]
                    existance = [c in self.df.columns for c in required_cols]
                    for c in required_cols:
                        if c not in self.df.columns:
                            raise Exception('{}がありません。'.format(c))
                    self.df['datetime'] = self.df[
                        r'検査日(yyyy/MM/dd HH:mm)'].map(
                            lambda d: datetime.datetime.strptime(
                                d, '%Y/%m/%d %H:%M'))
                    min_date, max_date = min(self.df['datetime']), max(
                        self.df['datetime'])
                    self.input_label.setText(
                        'ファイル名：{}、総数：{}\n期間：{} ~ {}'.format(
                            Path(fileName).name, len(self.df),
                            min_date.date().strftime('%Y/%m/%d'),
                            max_date.date().strftime('%Y/%m/%d')))

                    self.task_queue.queue.clear()
                    [self.task_queue.put(oid) for oid in self.df[r'オーダー番号']]
                    self.update_button_state()
                except Exception as e:
                    logger.error(e)
                    dialog = QErrorMessage(self)
                    dialog.setWindowTitle(r'読み込みエラー')
                    dialog.showMessage(r'無効なファイルです。{}'.format(str(e)))

        self.stop_button.clicked.connect(on_stop_button_clicked)
        self.start_button.clicked.connect(on_start_button_clicked)

        period_gropu = QGroupBox(r'実行時間帯')
        period_gropu.setLayout(QHBoxLayout())
        period_gropu.layout().addWidget(QLabel('Start', self))
        self.start_time = TimeEdit()
        self.start_time.setText('1900')
        self.config_widgets.append(self.start_time)
        period_gropu.layout().addWidget(self.start_time)
        period_gropu.layout().addWidget(QLabel('Stop', self))
        self.stop_time = TimeEdit()
        self.stop_time.setText('0700')
        self.config_widgets.append(self.stop_time)
        period_gropu.layout().addWidget(self.stop_time)

        output_group = QGroupBox(r'出力フォルダ')
        output_group.setLayout(QHBoxLayout())
        self.output_edit = QLineEdit()
        self.output_edit.setEnabled(False)
        output_group.layout().addWidget(self.output_edit)
        output_button = QPushButton(r'選択...')
        output_button.clicked.connect(on_browse_button_clicked)
        self.config_widgets.append(output_button)
        output_group.layout().addWidget(output_button)

        input_group = QGroupBox(r'患者リスト')
        input_group.setLayout(QVBoxLayout())
        input_button = QPushButton(r'リストを開く')
        input_button.clicked.connect(on_input_button_clicked)
        self.config_widgets.append(input_button)
        input_group.layout().addWidget(input_button)
        self.input_label = QLabel('リストがありません', self)
        self.input_label.setAlignment(Qt.AlignCenter)
        input_group.layout().addWidget(self.input_label)

        layout = QVBoxLayout()
        layout.addWidget(period_gropu)
        layout.addWidget(output_group)
        layout.addWidget(input_group)
        layout.addStretch()

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.stop_button)
        bottom_layout.addWidget(self.start_button)

        layout.addLayout(bottom_layout)
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.statusBar().setStyleSheet('background-color: #FFF8DC;')
        self.statusBar().showMessage('App started.', 2000)
        self.statusBar().addPermanentWidget(ClockLabel(self))

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
    window = MainWindow()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
