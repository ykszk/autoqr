import sys
import argparse
from pathlib import Path
import pandas as pd
from logzero import logger


def main():
    parser = argparse.ArgumentParser(description='Concatenate csv files.')
    parser.add_argument('input',
                        help="Input filename: %(default)s",
                        metavar='<input>',
                        nargs='+')
    parser.add_argument('--output',
                        help="Output filename",
                        metavar='<output>',
                        required=True)
    parser.add_argument('--sort',
                        help="Sort csv by specified column",
                        metavar='<column>')
    parser.add_argument('--descend',
                        help="Sort in descend order",
                        action='store_true')
    parser.add_argument('--drop', help="Drop duplicates", action='store_true')

    args = parser.parse_args()

    dfs = []
    for input_filename in args.input:
        df = pd.read_csv(input_filename)
        dfs.append(df)
        logger.info('%s : %d', input_filename, len(df))

    df = pd.concat(dfs)
    if args.sort is not None:
        df.sort_values(args.sort, inplace=True, ascending=not args.descend)
    if args.drop:
        df.drop_duplicates(inplace=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    logger.info('%s : %d', output, len(df))
    df.to_csv(output, index=False)


if __name__ == "__main__":
    sys.exit(main())
