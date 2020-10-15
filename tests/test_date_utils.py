import unittest
from datetime import datetime

import date_utils


class TestDateUtils(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestDateUtils, self).__init__(*args, **kwargs)

    def test_parse_date(self):
        pairs = [('20000101', datetime(2000, 1, 1)),
                 ('20101014', datetime(2010, 10, 14))]
        for args, output in pairs:
            self.assertEqual(date_utils.parse_date(args), output)

    def test_date2str(self):
        pairs = [('20000101', datetime(2000, 1, 1)),
                 ('20101014', datetime(2010, 10, 14))]
        for output, args in pairs:
            self.assertEqual(date_utils.date2str(args), output)

    def test_split(self):
        start = datetime(2000, 1, 1)
        end = datetime(2000, 1, 10)

        # step = 1
        split_result = list(date_utils.split(start, end, 1))
        self.assertEqual(split_result[0][0], start)
        self.assertEqual(split_result[0][1], datetime(2000, 1, 1))
        self.assertEqual(split_result[1][0], datetime(2000, 1, 2))
        self.assertEqual(split_result[1][1], datetime(2000, 1, 2))
        self.assertEqual(split_result[-1][0], end)
        self.assertEqual(split_result[-1][1], end)

        # step = 2
        split_result = list(date_utils.split(start, end, 2))
        self.assertEqual(split_result[0][0], start)
        self.assertEqual(split_result[0][1], datetime(2000, 1, 2))
        self.assertEqual(split_result[1][0], datetime(2000, 1, 3))
        self.assertEqual(split_result[1][1], datetime(2000, 1, 4))
        self.assertEqual(split_result[-1][0], datetime(2000, 1, 9))
        self.assertEqual(split_result[-1][1], end)

        # step = 2, one day
        split_result = list(date_utils.split(start, start, 2))
        self.assertEqual(split_result[0][0], start)
        self.assertEqual(split_result[0][1], start)

        # step = 3
        split_result = list(date_utils.split(start, end, 3))
        self.assertEqual(split_result[0][0], start)
        self.assertEqual(split_result[0][1], datetime(2000, 1, 3))
        self.assertEqual(split_result[1][0], datetime(2000, 1, 4))
        self.assertEqual(split_result[1][1], datetime(2000, 1, 6))
        self.assertEqual(split_result[-1][0], datetime(2000, 1, 10))
        self.assertEqual(split_result[-1][1], end)

        # over month, step = 3
        start = datetime(2000, 1, 1)
        end = datetime(2000, 2, 10)
        split_result = list(date_utils.split(start, end, 3))
        self.assertEqual(split_result[0][0], start)
        self.assertEqual(split_result[0][1], datetime(2000, 1, 3))
        self.assertEqual(split_result[1][0], datetime(2000, 1, 4))
        self.assertEqual(split_result[1][1], datetime(2000, 1, 6))
        self.assertEqual(split_result[-1][0], datetime(2000, 2, 9))
        self.assertEqual(split_result[-1][1], end)

        # over year, step = 3
        start = datetime(2000, 12, 30)
        end = datetime(2001, 1, 10)
        split_result = list(date_utils.split(start, end, 3))
        self.assertEqual(split_result[0][0], start)
        self.assertEqual(split_result[0][1], datetime(2001, 1, 1))
        self.assertEqual(split_result[1][0], datetime(2001, 1, 2))
        self.assertEqual(split_result[1][1], datetime(2001, 1, 4))
        self.assertEqual(split_result[-1][0], datetime(2001, 1, 8))
        self.assertEqual(split_result[-1][1], end)
