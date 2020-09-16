import os
from logzero import logger

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QPushButton, QButtonGroup, QRadioButton, QGroupBox
from PyQt5.QtGui import QFont

from clock_label import ClockLabel

app = QApplication([])
app.setStyle('Fusion')

if os.name == 'nt':
    font = QFont("Courier New", pointSize=10)
    font.setStyleHint(QFont.Monospace)
    app.setFont(font)

MSG_DURATION = 2000


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init()

    def init(self):
        central = QWidget(self)
        self.setWindowTitle('Auto Q/R')
        self.setMinimumSize(512, 512)

        stop_button = QPushButton('Stop')
        start_button = QPushButton('Start')

        def on_start_button_clicked():
            logger.info('start button pressed')

        def on_toggle(button, is_on):
            if is_on:
                msg = '{} Level selected'.format(button.text())
                logger.info(msg)
                self.statusBar().showMessage(msg, MSG_DURATION)

        start_button.clicked.connect(on_start_button_clicked)

        self.level_buttons = QButtonGroup()
        self.level_buttons.setExclusive(True)
        self.level_group = QGroupBox('Q/R Level')
        self.level_group.setLayout(QVBoxLayout())
        patient_level_button = QRadioButton('Patient')
        study_level_button = QRadioButton('Study')
        series_level_button = QRadioButton('Series')
        for b in [
                patient_level_button, study_level_button, series_level_button
        ]:
            self.level_buttons.addButton(b)
            self.level_group.layout().addWidget(b)
        patient_level_button.setChecked(True)
        self.level_buttons.buttonToggled.connect(on_toggle)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.level_group)
        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addStretch()

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(stop_button)
        bottom_layout.addWidget(start_button)

        layout.addLayout(bottom_layout)
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.statusBar().setStyleSheet('border: 0; background-color: #FFF8DC;')
        self.statusBar().showMessage('App started.', 2000)
        self.statusBar().addPermanentWidget(ClockLabel(self))


window = MainWindow()
window.show()
app.exec_()
