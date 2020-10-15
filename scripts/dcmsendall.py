import sys
import argparse
from pathlib import Path
import subprocess
from logzero import logger
import toml

logger.setLevel('DEBUG')


def main():
    parser = argparse.ArgumentParser(
        description=
        'Don\'t use this. Use dcmtk with --scan-directories --recurse. (Old desc.) Send all dicom files.'
    )
    parser.add_argument('input',
                        help="Input directory: %(default)s",
                        metavar='<input>')
    parser.add_argument(
        '-d',
        '--depth',
        help="Depth of dicom containing directories. Default:%(default)s",
        metavar='<dir>',
        default=1,
        type=int)
    parser.add_argument('--dicom_server',
                        help='IP address',
                        metavar='<addr>',
                        type=str)
    parser.add_argument('--port',
                        help='Port number',
                        metavar='<port>',
                        default=104,
                        type=int)
    parser.add_argument('--aet',
                        help='My AE title.',
                        metavar='<str>',
                        default='DCMSEND',
                        type=str)
    parser.add_argument('--aec',
                        help='Called (server\'s) AE title.',
                        metavar='<str>',
                        default='ANY-SCP',
                        type=str)
    parser.add_argument('--dcmtk_bindir',
                        help='Directory containing dcmsend.',
                        metavar='<str>',
                        default='',
                        type=str)

    parser.add_argument('--config',
                        help='TOML config file.',
                        metavar='<filename>',
                        type=str)

    parser.add_argument('--dryrun', help="Dryrun", action='store_true')

    args = parser.parse_args()

    config = toml.load(args.config)

    for attr in ['dicom_server', 'port', 'aet', 'aec', 'dcmtk_bindir']:
        if attr.upper() in config.keys():
            logger.info('Set from toml:%s=%s', attr, config[attr.upper()])
            setattr(args, attr, config[attr.upper()])

    dcmsend = str(Path(args.dcmtk_bindir) / 'dcmsend')
    try:
        subprocess.check_call([dcmsend, '-h'], stdout=subprocess.DEVNULL)
    except Exception as e:
        logger.error(e)
        print('Failed to find dcmsend')
        return 1

    base_args = [
        dcmsend, args.dicom_server, args.port, '-aet', args.aet, '-aec',
        args.aec, '--scan-directories'
    ]

    root_dir = Path(args.input)
    glob_pattern = '/'.join(['*'] * args.depth)
    logger.debug('glob %s', glob_pattern)
    for indir in [
            d for d in sorted(root_dir.glob(glob_pattern)) if d.is_dir()
    ]:
        logger.info('Send %s', indir)
        send_args = base_args + [str(indir)]
        logger.debug(' '.join(send_args))
        if args.dryrun:
            continue
        subprocess.check_call(send_args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
