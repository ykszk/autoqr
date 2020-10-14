import argparse
import sys
from datetime import datetime, timedelta

import pandas as pd
from pydicom.dataset import Dataset
import pynetdicom
import logzero
from logzero import logger

import qr
import settings
import date_utils

EXT_TABLE = {
    '.csv': 'to_csv',
    '.xlsx': 'to_excel',
}


def main():
    parser = argparse.ArgumentParser(description='Range based DICOM query.')
    parser.add_argument('start',
                        help="Range start. (YYYYmmdd) e.g. 20201014",
                        metavar='<start>')
    parser.add_argument('end', help="Range end. (YYYYmmdd)", metavar='<end>')
    parser.add_argument('--output',
                        help="Output filename. Default: <start>-<end>.csv",
                        metavar='<output>')
    parser.add_argument(
        '--step',
        help="Step size for query range in days. Default: %(default)s",
        default=2,
        type=int,
        metavar='<int>')
    parser.add_argument(
        '--ext',
        help=
        "File extension for the output. Default: %(default)s. Choices: [%(choices)s]",
        default='.csv',
        choices=EXT_TABLE.keys(),
        metavar='<ext>')
    parser.add_argument(
        '--qrlevel',
        help=
        "Query retrieve level. Default: %(default)s. Choices: [%(choices)s]",
        default='STUDY',
        choices=['PATIENT', 'STUDY', 'SERIES'],
        metavar='<level>')
    parser.add_argument(
        '--loglevel',
        help="Loglevel. default:%(default)s. choices:[%(choices)s]",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='DEBUG',
        metavar='<level>')

    args = parser.parse_args()

    logger.setLevel(args.loglevel)

    start_date = date_utils.parse_date(args.start)
    end_date = date_utils.parse_date(args.end)
    if start_date > end_date:
        print('Invalid range: start > end')
        return 1

    output_filename = args.output or '{}-{}{}'.format(args.start, args.end,
                                                      args.ext)
    logger.debug('Output filename:%s', output_filename)

    date_delta = end_date - start_date
    logger.info('%s - %s (%s days)', args.start, args.end, date_delta.days + 1)

    attributes = [
        'PatientID', 'Modality', 'StudyDescription', 'AccessionNumber',
        'StudyInstanceUID'
    ]

    all_result = []
    for part_start, part_end in date_utils.split(start_date, end_date,
                                                 args.step):
        study_date = '{}-{}'.format(date_utils.date2str(part_start),
                                    date_utils.date2str(part_end))
        print(study_date)

        ds = Dataset()
        ds.StudyDate = study_date
        ds.QueryRetrieveLevel = args.qrlevel
        for attr in attributes:
            setattr(ds, attr, '')

        query_result = qr.query(ds, logger=logger)
        if query_result:
            all_result.extend([[getattr(r, attr) for attr in attributes]
                               for r in query_result])

    df = pd.DataFrame(all_result, columns=attributes)
    getattr(df, EXT_TABLE[args.ext])(output_filename, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
