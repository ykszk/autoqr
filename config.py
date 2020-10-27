from pathlib import Path
import toml
from logzero import logger as default_logger


class Defaults():
    def __init__(self):
        self.DICOM_SERVER = 'localhost'  # DICOM server's IP address or hostname
        self.__PORT = 4242  # DICOM server's port
        self.AEC = 'ANY-SCP'  # DICOM server's AET
        self.AETS = ['AUTOQR']  # Client's application Entity Title
        self.START_TIME = '1800'
        self.STOP_TIME = '0700'
        self.DCMTK_BINDIR = ''
        self.__N_THREADS = 1
        self.__RECEIVE_PORTS = [104]
        self.COL_ACCESSION_NUMBER = 'AccessionNumber'
        self.COL_STUDY_INSTANCE_UID = 'StudyInstanceUID'
        self.COL_STUDY_DATE = 'StudyDate'
        self.COL_PATIENT_ID = 'PatientID'
        self.DATETIME_FORMAT = '%Y%m%d'

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
    def RECEIVE_PORTS(self):
        return self.__RECEIVE_PORTS

    @RECEIVE_PORTS.setter
    def RECEIVE_PORTS(self, port_str: str):
        self.__RECEIVE_PORTS = [int(e) for e in port_str]

    def load(self, filename, logger=None):
        with open(filename, encoding='utf8') as f:
            config = toml.load(f)
        vs = [v for v in dir(self) if not v.startswith('__')]
        for key in config.keys():
            if key in vs:
                if logger:
                    logger.info('Reset %s = %s', key, config[key])
                setattr(settings, key, config[key])
            elif logger:
                logger.warning('%s is invalid config key', key)


settings = Defaults()
settings.load(Path(__file__).parent / 'config.toml', default_logger)
