from pathlib import Path
import subprocess
import tempfile
import logging
import threading
import shutil
from collections import namedtuple
from concurrent.futures.thread import ThreadPoolExecutor
import pydicom
from pydicom.dataset import Dataset
from pynetdicom import AE, evt, build_role
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelFind
from pynetdicom.sop_class import (PatientRootQueryRetrieveInformationModelGet,
                                  CTImageStorage,
                                  PositronEmissionTomographyImageStorage)

from logzero import setup_logger

from config import settings
import anonymize
import hash_utils

default_logger = setup_logger()
default_logger.setLevel(logging.DEBUG)

logging.getLogger('pynetdicom').setLevel(logging.WARNING)

thread_pool = ThreadPoolExecutor(max_workers=settings.N_THREADS)

ConnectionInformation = namedtuple(
    'ConnectionInformation', ['server', 'aec', 'port', 'aet', 'receive_port'])


def query(ds: Dataset, server=None, aec=None, port=None, logger=None):
    '''
    Args:
        aec (str): Optional. AEC. default is settings.AECS[0]
        port (int): Optional. Server port. default is settings.PORTS[0]
    '''
    logger = logger or default_logger
    logger.debug('start query')
    if server is None:
        server = settings.DICOM_SERVERS[0]
    if aec is None:
        aec = settings.AECS[0]
    if port is None:
        port = settings.PORTS[0]
    ae = AE(ae_title=settings.AETS[0])
    ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
    ae.associate(server, port, ae_title=aec)
    if len(ae.active_associations) == 0:
        raise RuntimeError('No association was established')
    assoc = ae.active_associations[0]
    if not assoc.is_established:
        raise RuntimeError('Association rejected, aborted or never connected')

    datasets = []

    responses = assoc.send_c_find(
        ds, PatientRootQueryRetrieveInformationModelFind)
    for (status, identifier) in responses:
        if not status:
            raise RuntimeError(
                'Connection timed out, was aborted or received invalid response'
            )
        if status.Status == 0xFF00:
            datasets.append(identifier)

    assoc.release()
    logger.debug('end query %d', len(datasets))
    return datasets


def retrieve_dcmtk(ds,
                   outdir,
                   aet,
                   receive_port,
                   server=None,
                   aec=None,
                   port=None,
                   logger=None):
    '''
    Retrieve using dcmtk.
    dcmtk is used because retrieving with pynetdicom is slow on a laptop for some reason.
    '''
    logger = logger or default_logger
    series_uid = ds.SeriesInstanceUID
    if not isinstance(series_uid, str):
        series_uid = '\\'.join(series_uid)
    logger.debug('start retrieve %s', series_uid)

    if server is None:
        aec = settings.DICOM_SERVERS[0]
    if aec is None:
        aec = settings.AECS[0]
    if port is None:
        port = settings.PORTS[0]
    base_arg = '{} {} {} -aet {} -aec {}'.format(
        Path(settings.DCMTK_BINDIR) / 'movescu', server, port, aet, aec)
    level_arg = '-k 0008,0052=SERIES'
    pid_arg = '-k 0010,0020={}'.format(ds.PatientID)
    study_arg = '-k 0020,000D={}'.format(ds.StudyInstanceUID)
    series_arg = '-k 0020,000E={}'.format(series_uid)
    od_arg = '-od {}'.format(outdir)

    args = sum([
        base_arg.split(),
        '+P {}'.format(receive_port).split(),
        level_arg.split(),
        pid_arg.split(),
        study_arg.split(),
        series_arg.split(),
        od_arg.split(),
    ], [])

    logger.debug(' '.join(args))
    subprocess.check_call(args)

    logger.debug('end retrieve %s', ds.SeriesInstanceUID)
    return


def qr_dcmtk(ds: Dataset,
             outdir,
             aet,
             receive_port,
             predicate=None,
             logger=None):
    logger = logger or default_logger
    found_datasets = query(ds, logger)
    if predicate is not None:
        found_datasets = [ds for ds in found_datasets if predicate(ds)]

    for found_ds in found_datasets:
        ds = Dataset()
        ds.QueryRetrieveLevel = 'SERIES'
        ds.PatientID = found_ds.PatientID
        ds.AccessionNumber = found_ds.AccessionNumber
        ds.StudyInstanceUID = found_ds.StudyInstanceUID
        ds.SeriesInstanceUID = found_ds.SeriesInstanceUID
        series_dir = outdir / found_ds.SeriesInstanceUID
        series_dir.mkdir(parents=True, exist_ok=True)
        retrieve_dcmtk(ds, series_dir, aet, receive_port, logger=logger)

    return found_datasets


def get_output_directory(basedir: Path, year: str, date: str, patient_id: str,
                         study_uid: str):
    '''
    Args:
        patient_id: Original PatientID
        study_uid: Original StudyInstanceUID
    '''
    ds = Dataset()
    ds.PatientID = patient_id
    ds.StudyInstanceUID = study_uid
    new_pid = anonymize.anonymize_patient_id(ds)
    new_study_uid = anonymize.anonymize_study_uid(ds)
    zipdir = basedir / year / date / new_pid / new_study_uid
    return zipdir


def qr_anonymize_save(PatientID: str,
                      AccessionNumber: str,
                      StudyInstanceUID: str,
                      outdir: str,
                      conn_info: ConnectionInformation,
                      predicate=None,
                      logger=None):
    '''
    Q/R and save
    '''
    logger = logger or default_logger
    ds = Dataset()
    ds.PatientID = PatientID
    ds.StudyDate = ''
    ds.StudyInstanceUID = ''
    ds.SeriesInstanceUID = ''
    ds.QueryRetrieveLevel = 'SERIES'
    ds.Modality = ''
    ds.StudyInstanceUID = StudyInstanceUID
    ds.SeriesDescription = ''
    ds.SeriesNumber = ''

    temp = tempfile.mkdtemp()
    tmp_dir = Path(temp)
    all_datasets = query(ds,
                         aec=conn_info.aec,
                         port=conn_info.port,
                         logger=logger)
    if len(all_datasets) == 0:
        raise RuntimeError('No result for query:%{}'.format(ds))

    if predicate is not None:
        all_datasets = [ds for ds in all_datasets if predicate(ds)]
        logger.debug('Filtering done %d', len(all_datasets))

    zip_root = Path(outdir)

    list_suid = [dcm.SeriesInstanceUID for dcm in all_datasets]
    dcm = all_datasets[0]
    new_pid = hash_utils.hash_id(dcm.PatientID)
    new_study_uid = anonymize.anonymize_study_uid(dcm)

    ds = Dataset()
    ds.PatientID = dcm.PatientID
    ds.StudyInstanceUID = dcm.StudyInstanceUID
    ds.SeriesInstanceUID = '\\'.join(list_suid)
    retrieve_dcmtk(ds,
                   temp,
                   conn_info.aet,
                   conn_info.receive_port,
                   server=conn_info.server,
                   aec=conn_info.aec,
                   port=conn_info.port,
                   logger=logger)

    def target():
        logger.info('Start anonymize %s', StudyInstanceUID)
        for dcm in all_datasets:
            series_dir = tmp_dir / dcm.SeriesInstanceUID
            series_dir.mkdir(parents=True, exist_ok=True)
        for dcm_fn in sorted(tmp_dir.glob('*')):
            if dcm_fn.is_dir():
                continue
            dcm = pydicom.dcmread(str(dcm_fn),
                                  specific_tags=['SeriesInstanceUID'],
                                  stop_before_pixels=True)
            shutil.move(str(dcm_fn),
                        tmp_dir / dcm.SeriesInstanceUID / dcm_fn.name)
        for dcm in all_datasets:
            year, date = dcm.StudyDate[:4], dcm.StudyDate[4:]
            new_series_uid = anonymize.anonymize_series_uid(dcm)
            zipdir = get_output_directory(zip_root, year, date, dcm.PatientID,
                                          dcm.StudyInstanceUID)
            zipdir.mkdir(parents=True, exist_ok=True)
            zip_filename = anonymize.get_available_filename(
                str(zipdir / new_series_uid), '.zip')

            anonymize.anonymize_dcm_dir(tmp_dir / dcm.SeriesInstanceUID,
                                        str(zip_filename))
        shutil.rmtree(temp)
        logger.info('End anonymize %s', StudyInstanceUID)

    thread_pool.submit(target)
    new_an = hash_utils.hash_id(
        AccessionNumber) if AccessionNumber != '' else ''
    return new_pid, new_an, new_study_uid, dcm.StudyDate


def shutdown():
    thread_pool.shutdown()


def is_original_image(ds: Dataset):
    return ds.SeriesNumber < 300


def main():
    ds = Dataset()
    ds.PatientID = '2Omc-Ajo60NctUzJpd4Q8w'
    ds.StudyInstanceUID = ''
    ds.SeriesInstanceUID = ''
    ds.QueryRetrieveLevel = 'SERIES'
    ds.Modality = ''
    ds.AccessionNumber = 'Ci5Lj86Rg4HrLuRLZjnqAA'
    ds.SeriesDescription = ''

    all_datasets = qr_dcmtk(ds, Path('.'), settings.AETS[0],
                            settings.RECEIVE_PORTS[0])
    print(len(all_datasets))


if __name__ == "__main__":
    main()
