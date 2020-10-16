import sys
import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser(
        description='Remove columns containing "original".')
    parser.add_argument('input',
                        help='Input csv filename: %(default)s',
                        metavar='<input>')
    parser.add_argument('output',
                        help='Output filename: %(default)s',
                        metavar='<output>')

    args = parser.parse_args()

    df = pd.read_csv(args.input, encoding='cp932')
    for column in df.columns:
        if 'original' in column.lower():
            del df[column]
    df.to_csv(args.output, index=False)
    return 0


if __name__ == '__main__':
    sys.exit(main())
