import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import argparse
from math import ceil
import pandas as pd
import pydicom
import toml
import hash_utils
import dcm_utils

from logging import basicConfig, getLogger, INFO
basicConfig(level=INFO, format='%(asctime)s %(levelname)s :%(message)s')
logger = getLogger(__name__)

SOP_UID_PREFIX = '11.'
STUDY_UID_PREFIX = '12.'
SERIES_UID_PREFIX = '13.'

MSSOPUID_TAG = (0x0002, 0x0003)  # media storage SOP instance UID
ImplClassUID_TAG = (0x0002, 0x0012)  # Implementation Class UID
IMPL_VERISON_NAME_TAG = (0x0002, 0x0013)
IMPL_VERISON_NAME = 'pydicom {}'.format(pydicom.__version__)

ACCESSION_N_TAG = (0x0008, 0x0050)  # accession number

SOPInstanceUID_TAG = (0x0008, 0x0018)  # SOP Instance UID

PID_TAG = (0x0010, 0x0020)
PATIENT_NAME_TAG = (0x0010, 0x0010)
STUDY_UID_TAG = (0x0020, 0x000d)
SERIES_UID_TAG = (0x0020, 0x000e)

REQ_PROC_COMMENT_TAG = (0x0040, 0x1400)

config = toml.load('config/tags.toml')
remove_rules = [dcm_utils.tag2int(r) for r in config['remove']]

with open('config/.salt') as f:
    salt = f.read().rstrip()

hash_utils.set_default_salt(salt)


def gen_sop_uid(dcm, base_uid, sop_prefix):
    suffix = '.'.join(base_uid.split('.')[-2:])
    return sop_prefix[:(64 - len(suffix) - 1)] + '.' + suffix


def anonymize_study_uid(dcm):
    new_pid = hash_utils.hash_id(dcm.PatientID)
    new_study_uid = pydicom.uid.generate_uid(
        prefix=pydicom.uid.PYDICOM_ROOT_UID + STUDY_UID_PREFIX,
        entropy_srcs=[new_pid, dcm[STUDY_UID_TAG].value])
    return new_study_uid


def anonymize_series_uid(dcm):
    new_pid = hash_utils.hash_id(dcm.PatientID)
    new_series_uid = pydicom.uid.generate_uid(
        prefix=pydicom.uid.PYDICOM_ROOT_UID + SERIES_UID_PREFIX,
        entropy_srcs=[new_pid, dcm[SERIES_UID_TAG].value])
    return new_series_uid


def anonymize_dcm(dcms, zip_filename):
    dcm = dcms[0]
    new_pid = hash_utils.hash_id(dcm.PatientID)

    replace_rules = []

    # file meta
    replace_rules.append((IMPL_VERISON_NAME_TAG, IMPL_VERISON_NAME))

    sop_prefix = pydicom.uid.generate_uid(
        prefix=pydicom.uid.PYDICOM_ROOT_UID + SOP_UID_PREFIX,
        entropy_srcs=[new_pid, dcm.file_meta[MSSOPUID_TAG].value])

    def anonymize_ms_sop_uid(dcm):
        uid = dcm.file_meta[MSSOPUID_TAG].value
        return gen_sop_uid(dcm, uid, sop_prefix)

    def anonymize_sop_uid(dcm):
        uid = dcm[SOPInstanceUID_TAG].value
        return gen_sop_uid(dcm, uid, sop_prefix)

    replace_rules.append((MSSOPUID_TAG, anonymize_ms_sop_uid))
    replace_rules.append((SOPInstanceUID_TAG, anonymize_sop_uid))

    # data
    replace_rules.append((PID_TAG, new_pid))
    replace_rules.append((PATIENT_NAME_TAG, new_pid))
    replace_rules.append(
        (ImplClassUID_TAG, pydicom.uid.PYDICOM_IMPLEMENTATION_UID))

    new_study_uid = anonymize_study_uid(dcm)
    replace_rules.append((STUDY_UID_TAG, new_study_uid))

    new_series_uid = anonymize_series_uid(dcm)
    replace_rules.append((SERIES_UID_TAG, new_series_uid))

    new_accession_n = hash_utils.hash_id(dcm[ACCESSION_N_TAG].value)
    replace_rules.append((ACCESSION_N_TAG, new_accession_n))

    dcm_generator = dcm_utils.DcmGenerator(dcms, replace_rules, remove_rules)
    name_format = '{{:0{}d}}.dcm'.format(ceil(len(dcms)))
    dcm_utils.dcms2zip([name_format.format(i) for i in range(len(dcms))],
                       dcm_generator,
                       1,
                       zip_filename,
                       verbose=False)

    return new_pid


def get_available_filename(left, right):
    if not Path(left + right).exists():
        return left + right
    i = 1
    while True:
        candidate = left + '_{}'.format(i) + right
        if not Path(left + '_{}'.format(i) + right).exists():
            return candidate
        i += 1
