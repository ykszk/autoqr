import sys
from pathlib import Path
import toml
from logzero import logger as default_logger


class Defaults():
    def __init__(self):
        self.DICOM_SERVERS = ['localhost'
                              ]  # DICOM server's IP address or hostname
        self.__PORTS = [4242]  # DICOM server's port
        self.AECS = ['ANY-SCP']  # DICOM server's AET
        self.AETS = ['AUTOQR']  # Client's application Entity Title
        self.__PERIODS = [('1800', '0700')]
        self.DCMTK_BINDIR = ''
        self.__N_THREADS = 1
        self.__RECEIVE_PORTS = [104]
        self.COL_ACCESSION_NUMBER = 'AccessionNumber'
        self.COL_STUDY_INSTANCE_UID = 'StudyInstanceUID'
        self.COL_STUDY_DATE = 'StudyDate'
        self.COL_PATIENT_ID = 'PatientID'
        self.DATETIME_FORMAT = '%Y%m%d'
        self.SKIP_EXISTING_STUDY = True
        self.__INTERVAL = 5

    @property
    def N_THREADS(self):
        return self.__N_THREADS

    @N_THREADS.setter
    def N_THREADS(self, n_str: str):
        self.__N_THREADS = int(n_str)

    @property
    def INTERVAL(self):
        return self.__INTERVAL

    @INTERVAL.setter
    def INTERVAL(self, int_str: str):
        self.__INTERVAL = int(int_str)

    @property
    def PORTS(self):
        return self.__PORTS

    @PORTS.setter
    def PORTS(self, port_str: str):
        self.__PORTS = [int(e) for e in port_str]

    @property
    def PERIODS(self):
        return self.__PERIODS

    @PERIODS.setter
    def PERIODS(self, periods):
        for p in periods:
            if len(p) != 2:
                default_logger.error(
                    'Invalid PERIODS in the config. Nested periods is expected (e.g. [["1800", "0600"]]): %s',
                    periods)
                sys.exit(1)
        self.__PERIODS = periods

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

    def validate_n_threads(self):
        if len(self.RECEIVE_PORTS) < self.N_THREADS:
            default_logger.error(
                'Invalid config. len(RECEIVE_PORTS) < N_THREADS (%d and %d)',
                len(self.RECEIVE_PORTS), self.N_THREADS)
            return False

        if len(self.AETS) < self.N_THREADS:
            default_logger.error(
                'Invalid N_THREADS config. len(AETS) < N_THREADS (%d and %d)',
                len(self.AETS), self.N_THREADS)
            return False

        return True

    def validate_server_config(self):
        if len(self.AECS) == len(self.DICOM_SERVERS) == len(self.PORTS):
            return True
        else:
            default_logger.error(
                'Invalid server config. len(AECS), len(DICOM_SERVERS) and len(PORTS) need to be the same value. (%d, %d and %d)',
                len(self.AECS), len(self.DICOM_SERVERS), len(self.PORTS))
            return False


settings = Defaults()
config_filename = Path(__file__).parent / 'config.toml'
if config_filename.exists():
    settings.load(config_filename, default_logger)
