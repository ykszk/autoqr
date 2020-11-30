import sys
import datetime
import subprocess
import argparse
import logging
from pathlib import Path
from threading import Lock
import logzero
from logzero import logger

from autoqr import AutoQR, open_csv, remove_existing, add_datetime

from config import settings

logger.setLevel(logging.DEBUG)


def main():
    parser = argparse.ArgumentParser(description='Auto Q/R.')
    parser.add_argument('csv_filename',
                        help="CSV filename",
                        metavar='<filename>')
    parser.add_argument('outdir', help="Output directory", metavar='<dirname>')
    parser.add_argument(
        '--logfile',
        help=
        "Log to the specified file. Specify '-' for no logfile. (Default:logs/%%y%%m%%d_%%H%%M%%S.log)",
        metavar='<filename>')

    parser.add_argument(
        '--loglevel',
        help="Loglevel. default:%(default)s. choices:[%(choices)s]",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='DEBUG',
        metavar='<str>')

    args = parser.parse_args()

    try:
        subprocess.check_call(
            [str(Path(settings.DCMTK_BINDIR) / 'movescu'), '-h'],
            stdout=subprocess.DEVNULL)
    except Exception as e:
        logger.error(e)
        return 1

    if args.logfile and args.logfile != '-':
        logzero.logfile(args.logfile, maxBytes=1e7, backupCount=256)
    else:
        logfile = Path('logs') / '{}.log'.format(
            datetime.datetime.today().strftime("%y%m%d_%H%M%S"))
        logfile.parent.mkdir(parents=True, exist_ok=True)
        logzero.logfile(logfile, maxBytes=1e7, backupCount=256)
    logger.setLevel(args.loglevel)

    if not settings.validate_n_threads():
        print('Invalid N_THREADS')
        return 1

    if not settings.validate_server_config():
        print('Server config error')
        return 1

    if len(settings.RECEIVE_PORTS) > settings.N_THREADS:
        logger.warning('N_THREADS < available ports (%s and %s)',
                       len(settings.RECEIVE_PORTS), settings.N_THREADS)

    outdir = Path(args.outdir)
    autoqr = AutoQR(args.outdir, logger)
    df = open_csv(args.csv_filename)
    add_datetime(df)
    if settings.SKIP_EXISTING_STUDY:
        logger.info('Skip existing')
        original_count = len(df)
        df = remove_existing(df, outdir)
        logger.info('Skipping result:%d -> %d', original_count, len(df))
    if len(df) == 0:
        print('No studies for Q/R')
        return 0
    autoqr.set_df(df)
    lock = Lock()  # lock to wait for the autoqr to finish
    lock.acquire()

    def on_job_done():
        logger.info('QR rate = %g / h', autoqr.rate)
        if autoqr.done_count + autoqr.error_count >= len(df):
            lock.release()

    outdir.mkdir(parents=True, exist_ok=True)
    autoqr.add_job_done_handler(on_job_done)
    autoqr.sched_event.start()

    lock.acquire()  # wait for the autoqr
    logger.info('Finalize')
    autoqr.finalize()
    logger.info('All done')

    return 0


if __name__ == '__main__':
    sys.exit(main())
