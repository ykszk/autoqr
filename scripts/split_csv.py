import sys
import argparse
from pathlib import Path
import math
import pandas as pd
from logzero import logger


def main():
    parser = argparse.ArgumentParser(description='Split csv file.')
    parser.add_argument('input',
                        help="Input filename: %(default)s",
                        metavar='<input>',
                        nargs='+')
    parser.add_argument('--output',
                        help="Output directory",
                        metavar='<directory>',
                        required=True)
    parser.add_argument('--size',
                        help="Maximum # of rows for a file",
                        metavar='<int>',
                        type=int,
                        required=True)
    parser.add_argument('--name',
                        help="Column name used for naming output",
                        metavar='<name>',
                        required=True)

    args = parser.parse_args()

    dfs = []
    for input_filename in args.input:
        dfs.append(pd.read_csv(input_filename, dtype=str))

    df = pd.concat(dfs)
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    for i in range(math.ceil(len(df) / args.size)):
        start = i * args.size
        end = min((i + 1) * args.size, len(df))
        sub = df[start:end]
        if args.name:
            stem = '{}-{}'.format(sub[args.name].iloc[0],
                                  sub[args.name].iloc[-1])
            filename = stem + '.csv'
            if (outdir / filename).exists():
                suffix = 1
                while True:
                    filename = stem + '_{}.csv'.format(suffix)
                    if not (outdir / filename).exists():
                        break
                    suffix += 1
        else:
            filename = '{}.csv'.format(i + 1)
        output = outdir / filename
        sub.to_csv(output, index=False)
        logger.info('%s : %d', output, len(sub))


if __name__ == "__main__":
    sys.exit(main())
