import unittest
from hm_clock import HMClock


class TestHMClock(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestHMClock, self).__init__(*args, **kwargs)

    def test_valid_from_str(self):
        pairs = [
            ('00:00', (0, 0)),
            ('23:00', (23, 0)),
            ('12:00', (12, 0)),
            ('12:30', (12, 30)),
            ('3:59', (3, 59)),
            ('15:5', (15, 5)),
        ]

        for args, ans in pairs:
            c = HMClock.from_str(args)
            self.assertEqual(c.hour, ans[0])
            self.assertEqual(c.minute, ans[1])

    def test_invalid_from_str(self):
        invalid_args = ['25:00', '-1:00', '12:70', '12:-5', '24:00', '12:60']
        for args in invalid_args:
            with self.assertRaises(ValueError):
                HMClock.from_str(args)

    def test_valid_from_minute(self):
        pairs = [((12 * 60 + 0), (12, 0)), ((15 * 60 + 15), (15, 15))]

        for minute, ans in pairs:
            c = HMClock.from_minute(minute)
            ans = HMClock(*ans)
            self.assertEqual(c, ans)

    def test_invalid_from_minute(self):
        invalid_args = [-100, 25 * 60]
        for args in invalid_args:
            with self.assertRaises(ValueError):
                HMClock.from_minute(args)

    def test_delta(self):
        pairs = [(('12:00', '6:00'), ('6:00')), (('3:00', '19:00'), ('8:00')),
                 (('6:30', '23:05'), ('7:25'))]

        for (end, start), ans in pairs:
            e, s = HMClock.from_str(end), HMClock.from_str(start)
            delta = e - s
            print(delta, ans)
            self.assertEqual(delta, HMClock.from_str(ans), '{}:{}'.format(
                (end, start), ans))

    def test_is_between(self):
        args = [
            ('00:00', '12:00', '15:00'),
            ('23:00', '3:30', '4:00'),  # over midnight
        ]

        for (start, between, end) in args:
            s, b, e = HMClock.from_str(start), HMClock.from_str(
                between), HMClock.from_str(end)
            self.assertTrue(b.is_between(s, e))

        args = [
            ('00:00', '23:15', '15:00'),
            ('23:00', '15:00', '4:00'),  # over midnight
        ]

        for (start, between, end) in args:
            s, b, e = HMClock.from_str(start), HMClock.from_str(
                between), HMClock.from_str(end)
            self.assertFalse(b.is_between(s, e))
