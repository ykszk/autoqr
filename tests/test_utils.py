import unittest
import tempfile
from pathlib import Path
import random
import pandas as pd
import utils


class TestCsvWriter(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestCsvWriter, self).__init__(*args, **kwargs)

    def test_no_write(self):
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir = Path(tempdir)
            filename = tempdir / 'test.csv'
            writer = utils.CsvWriter(filename, 'c1')
            del writer
            self.assertFalse(filename.exists())

    def test_writes(self):
        columns = ['c1', 'c2', 'c3']
        random_data = [[random.randint(0, 100) for _ in range(3)]
                       for _ in range(3)]
        df = pd.DataFrame(random_data, columns=columns)
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir = Path(tempdir)
            filename = tempdir / 'test.csv'
            writer = utils.CsvWriter(filename, header=','.join(columns))
            for row in random_data:
                writer.add_line(','.join([str(e) for e in row]))
            del writer
            df_read = pd.read_csv(filename, encoding='cp932')
        self.assertTrue(df.equals(df_read))
