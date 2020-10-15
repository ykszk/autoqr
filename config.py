from pathlib import Path
import toml


class Defaults():
    def __init__(self):
        self.DICOM_SERVER = 'localhost'  # DICOM server's IP address or hostname
        self.__PORT = 4242  # DICOM server's port
        self.AEC = 'ANY-SCP'  # DICOM server's AET
        self.AET = 'AUTOQR'  # Client's application Entity Title
        self.START_TIME = '1800'
        self.STOP_TIME = '0700'
        self.__N_THREADS = 2
        self.DCMTK_BINDIR = ''
        self.__RECEIVE_PORT = 4200
        self.COL_ACCESSION_NUMBER = 'オーダー番号'
        self.COL_STUDY_DATE = '検査日(yyyy/MM/dd HH:mm)'
        self.COL_PATIENT_ID = '受診者ID'
        self.DATETIME_FORMAT = '%Y/%m/%d %H:%M'

    @property
    def N_THREADS(self):
        return self.__N_THREADS

    @N_THREADS.setter
    def N_THREADS(self, n_str: str):
        self.__N_THREADS = int(n_str)

    @property
    def PORT(self):
        return self.__PORT

    @PORT.setter
    def PORT(self, port_str: str):
        self.__PORT = int(port_str)

    @property
    def RECEIVE_PORT(self):
        return self.__RECEIVE_PORT

    @RECEIVE_PORT.setter
    def RECEIVE_PORT(self, port_str: str):
        self.__RECEIVE_PORT = int(port_str)

    def load(self, filename, logger=None):
        with open(filename, encoding='utf8') as f:
            config = toml.load(f)
        vs = [v for v in dir(self) if not v.startswith('__')]
        for key in config.keys():
            if key in vs:
                if logger:
                    logger.info('Reset {} with {}'.format(key, config[key]))
                setattr(settings, key, config[key])


settings = Defaults()
settings.load(Path(__file__).parent / 'config.toml')
