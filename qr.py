from pathlib import Path
import subprocess, tempfile
import logging
import threading
import shutil
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


def associate():
    ae = AE(ae_title=settings.AET)
    ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
    assoc = ae.associate(settings.DICOM_SERVER,
                         settings.PORT,
                         ae_title=settings.AEC)
    if not assoc.is_established:
        raise RuntimeError('Association rejected, aborted or never connected')
    return assoc


def query(ds: Dataset, logger=None, ae=None):
    '''
    Args:
        ae: AE with an association
    '''
    logger = logger or default_logger
    logger.debug('start query')
    if ae is None:
        ae = AE(ae_title=settings.AET)
        ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
        ae.associate(settings.DICOM_SERVER,
                     settings.PORT,
                     ae_title=settings.AEC)
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


def retrieve(ds, logger=None):
    logger = logger or default_logger
    logger.debug('start retrieve')

    stored_datasets = []

    def handle_store(event):
        ds = event.dataset
        ds.file_meta = event.file_meta

        stored_datasets.append(ds)  # append is thread safe
        return 0x0000

    handlers = [(evt.EVT_C_STORE, handle_store)]

    ae = AE(ae_title=settings.AET)

    ae.add_requested_context(PatientRootQueryRetrieveInformationModelGet)
    ae.add_requested_context(CTImageStorage)
    ae.add_requested_context(PositronEmissionTomographyImageStorage)
    role_ct = build_role(CTImageStorage, scp_role=True)
    role_pt = build_role(PositronEmissionTomographyImageStorage, scp_role=True)

    assoc = ae.associate(settings.DICOM_SERVER,
                         settings.PORT,
                         ext_neg=[role_ct, role_pt],
                         evt_handlers=handlers,
                         ae_title=settings.AEC)
    if not assoc.is_established:
        raise RuntimeError('Association rejected, aborted or never connected')

    responses = assoc.send_c_get(ds,
                                 PatientRootQueryRetrieveInformationModelGet)
    for (status, _) in responses:
        if not status:
            raise RuntimeError(
                'Connection timed out, was aborted or received invalid response'
            )

    assoc.release()
    logger.debug('end retrieve %d', len(stored_datasets))
    return stored_datasets


def retrieve_dcmtk(ds, outdir, logger=None):
    '''
    Retrieve using dcmtk.
    dcmtk is used because retrieving with pynetdicom is slow on a laptop for some reason.
    '''
    logger = logger or default_logger
    series_uid = ds.SeriesInstanceUID
    if not isinstance(series_uid, str):
        series_uid = '\\'.join(series_uid)
    logger.debug('start retrieve %s', series_uid)

    base_arg = '{} {} {} -aet {} -aec {}'.format(
        Path(settings.DCMTK_BINDIR) / 'movescu', settings.DICOM_SERVER,
        settings.PORT, settings.AET, settings.AEC)
    level_arg = '-k 0008,0052=SERIES'
    pid_arg = '-k 0010,0020={}'.format(ds.PatientID)
    study_arg = '-k 0020,000D={}'.format(ds.StudyInstanceUID)
    series_arg = '-k 0020,000E={}'.format(series_uid)
    od_arg = '-od {}'.format(outdir)

    args = sum([
        base_arg.split(),
        '+P {}'.format(settings.RECEIVE_PORT).split(),
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


def qr(ds: Dataset, predicate=None, logger=None):
    logger = logger or default_logger
    found_datasets = query(ds, logger)
    if predicate is not None:
        found_datasets = [ds for ds in found_datasets if predicate(ds)]

    all_datasets = []
    for found_ds in found_datasets:
        ds = Dataset()
        ds.QueryRetrieveLevel = 'SERIES'
        ds.PatientID = found_ds.PatientID
        ds.AccessionNumber = found_ds.AccessionNumber
        ds.StudyInstanceUID = found_ds.StudyInstanceUID
        ds.SeriesInstanceUID = found_ds.SeriesInstanceUID
        datasets = retrieve(ds, logger)
        all_datasets.append(datasets)

    return all_datasets


def qr_dcmtk(ds: Dataset, outdir, predicate=None, logger=None):
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
        retrieve_dcmtk(ds, series_dir, logger)

    return found_datasets


def qr_anonymize_save(PatientID: str,
                      AccessionNumber: str,
                      StudyInstanceUID: str,
                      outdir: str,
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
    # ds.AccessionNumber = AccessionNumber
    ds.StudyInstanceUID = StudyInstanceUID
    ds.SeriesDescription = ''
    ds.ImageType = ''

    temp = tempfile.mkdtemp()
    tmp_dir = Path(temp)
    all_datasets = query(ds, logger=logger)

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
    retrieve_dcmtk(ds, temp, logger)

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
            new_pid = hash_utils.hash_id(dcm.PatientID)
            new_study_uid = anonymize.anonymize_study_uid(dcm)
            new_series_uid = anonymize.anonymize_series_uid(dcm)
            zipdir = zip_root / year / date / new_pid / new_study_uid
            zipdir.mkdir(parents=True, exist_ok=True)
            zip_filename = anonymize.get_available_filename(
                str(zipdir / new_series_uid), '.zip')

            anonymize.anonymize_dcm_dir(tmp_dir / dcm.SeriesInstanceUID,
                                        str(zip_filename))
        shutil.rmtree(temp)
        logger.info('End anonymize %s', StudyInstanceUID)

    t = threading.Thread(target=target)
    t.start()
    new_an = hash_utils.hash_id(
        AccessionNumber) if AccessionNumber != '' else ''
    return new_pid, new_an, new_study_uid, dcm.StudyDate


def is_original_image(ds: Dataset):
    try:
        if ds.ImageType[0] == 'ORIGINAL':
            return True
    except Exception:
        pass

    return False


def main():
    ds = Dataset()
    ds.PatientID = '2Omc-Ajo60NctUzJpd4Q8w'
    ds.StudyInstanceUID = ''
    ds.SeriesInstanceUID = ''
    ds.QueryRetrieveLevel = 'SERIES'
    ds.Modality = ''
    ds.AccessionNumber = 'Ci5Lj86Rg4HrLuRLZjnqAA'
    ds.SeriesDescription = ''

    all_datasets = qr(ds)
    print(len(all_datasets))


if __name__ == "__main__":
    main()
