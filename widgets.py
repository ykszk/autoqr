import datetime

from PyQt5.QtWidgets import QLabel, QLineEdit, QFrame
from PyQt5.QtCore import QTimer, QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import Qt


class VLine(QFrame):
    # a simple VLine, like the one you get from designer
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(self.VLine | self.Sunken)


class ClockLabel(QLabel):
    def __init__(self,
                 parent=None,
                 format='%H:%M:%S',
                 tooltip_format='%Y/%m/%d'):
        '''
        Args:
            format: datetime format
            tooltip_format: datetime format for the tooltip
        '''
        super().__init__(parent)
        self.format = format
        self.tooltip_format = tooltip_format
        self.updateClock()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateClock)
        self.timer.start(1000)

    def updateClock(self):
        dt = datetime.datetime.today()
        self.setToolTip(dt.strftime(self.tooltip_format))
        self.setText(dt.strftime(self.format))


class TimeEdit(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setInputMask('99:99')
        validator = QRegExpValidator(self)
        validator.setRegExp(QRegExp('^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'))
        self.setValidator(validator)
