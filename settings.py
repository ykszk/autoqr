import os
from pathlib import Path
from dotenv import load_dotenv

dotenv_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path)

DICOM_SERVER = os.getenv('DICOM_SERVER')
AEC = os.getenv('AEC')
AET = os.getenv('AET')
