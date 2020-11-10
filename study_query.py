import argparse
import sys
import io

import pandas as pd
from pydicom.dataset import Dataset
from logzero import logger

import qr
from utils import swallow_exceptions

EXT_TABLE = {
    '.csv': 'to_csv',
    '.xlsx': 'to_excel',
}


def main():
    parser = argparse.ArgumentParser(
        description='Query by study instance UID.')
    parser.add_argument('UID', help="Study instance UID", metavar='<UID>')
    parser.add_argument(
        '-a',
        '--attr',
        help="Additional attribute(s). Can be set multiple times.",
        metavar='<str>',
        default=[],
        action='append')
    parser.add_argument(
        '--output',
        help="Output filename. Specify - to use stdout. Default: <UID>.csv",
        metavar='<output>')
    parser.add_argument(
        '--loglevel',
        help="Loglevel. default:%(default)s. choices:[%(choices)s]",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        metavar='<level>')

    args = parser.parse_args()

    logger.setLevel(args.loglevel)

    output_filename = args.output or '{}.csv'.format(args.UID)
    logger.debug('Output filename:%s', output_filename)

    attributes = [
        'PatientID', 'Modality', 'StudyDate', 'StudyDescription',
        'AccessionNumber', 'StudyInstanceUID', 'SeriesInstanceUID',
        'SeriesDescription'
    ]

    attributes.extend(args.attr)

    ds = Dataset()
    for attr in attributes:
        setattr(ds, attr, '')
    ds.QueryRetrieveLevel = 'SERIES'
    ds.StudyInstanceUID = args.UID

    query_result = qr.query(ds, logger=logger)
    df = pd.DataFrame(
        [[swallow_exceptions(logger)(getattr)(r, attr) for attr in attributes]
         for r in query_result],
        columns=attributes)
    logger.info('%d query results', len(df))
    if output_filename == '-':
        s = io.StringIO()
        df.to_csv(s)
        print(s.getvalue())
    else:
        df.to_csv(output_filename, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
