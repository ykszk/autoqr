import os
from pathlib import Path
from dotenv import load_dotenv

dotenv_path = Path(__file__).parent / 'config' / '.env'
load_dotenv(dotenv_path)

DICOM_SERVER = os.getenv('DICOM_SERVER')
PORT = int(os.getenv('PORT'))
AEC = os.getenv('AEC')
AET = os.getenv('AET')
