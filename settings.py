import os
from pathlib import Path
from dotenv import load_dotenv

dotenv_path = Path(__file__).parent / 'config' / '.env'
load_dotenv(dotenv_path, encoding='utf8')

DICOM_SERVER = os.getenv('DICOM_SERVER')
PORT = int(os.getenv('PORT'))
AEC = os.getenv('AEC')
AET = os.getenv('AET')

START_TIME = os.getenv('START_TIME')
STOP_TIME = os.getenv('STOP_TIME')

N_THREADS = int(os.getenv('N_THREADS'))
GETSCU = os.getenv('GETSCU')

COL_ACCESSION_NUMBER = os.getenv('COL_ACCESSION_NUMBER')
COL_STUDY_DATE = os.getenv('COL_STUDY_DATE')
COL_PATIENT_ID = os.getenv('COL_PATIENT_ID')
DATETIME_FORMAT = os.getenv('DATETIME_FORMAT')
