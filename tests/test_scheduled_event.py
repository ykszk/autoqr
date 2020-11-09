import unittest
import time

import freezegun

from scheduled_event import ScheduledEvent, Periods
from hm_clock import HMClock


class TestPeriods(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestPeriods, self).__init__(*args, **kwargs)

    def test_instanciation(self):
        expected_periods = Periods([('0600', '0800'), ('1000', '1500')])
        se = ScheduledEvent([('0600', '0800'), ('1000', '1500')])
        self.assertEqual(expected_periods, se.periods)

        # ordering
        periods = Periods([('1000', '1500'), ('0600', '0800')])
        self.assertEqual(expected_periods, periods)

    def test_overlap(self):
        with self.assertRaises(RuntimeError):
            ScheduledEvent([('1000', '1500'), ('1200', '2200')])

        # over midnight
        with self.assertRaises(RuntimeError):
            ScheduledEvent([('2220', '0530'), ('0200', '0300')])

    def test_between(self):
        periods = Periods([('0600', '0800'), ('1500', '2300')])
        self.assertFalse(periods.between(HMClock(18, 0)) is None)
        self.assertTrue(periods.between(HMClock(10, 0)) is None)

    def test_next(self):
        periods = Periods([('0600', '0800'), ('1500', '2300')])
        for clock, expected in [
            (HMClock(3, 0), HMClock(6, 0)),
            (HMClock(18, 0), HMClock(6, 0)),
            (HMClock(23, 30), HMClock(6, 0)),
            (HMClock(7, 0), HMClock(15, 0)),
            (HMClock(10, 0), HMClock(15, 0)),
        ]:
            c_next = periods.next(clock)
            self.assertEqual(expected, c_next.start)


class TestScheduledEvent(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestScheduledEvent, self).__init__(*args, **kwargs)

    def test_immediate_start(self):
        se = ScheduledEvent([('0600', '0800'), ('1000', '1500')])
        with freezegun.freeze_time('2020-1-1 12:00:00'):
            se.start()
            self.assertTrue(se.event.is_set())

    def test_scheduled_start(self):
        se = ScheduledEvent([('0600', '0800'), ('1000', '1500')])
        with freezegun.freeze_time('2020-1-1 5:59:59', tick=True):
            self.assertFalse(se.event.is_set())
            se.start()
            self.assertFalse(se.event.is_set())
            time.sleep(2)
            self.assertTrue(se.event.is_set())

    def test_scheduled_end(self):
        se = ScheduledEvent([('0600', '0800'), ('1000', '1500')])
        with freezegun.freeze_time('2020-1-1 7:59:59', tick=True):
            self.assertFalse(se.event.is_set())
            se.start()
            self.assertTrue(se.event.is_set())
            time.sleep(2)
            self.assertFalse(se.event.is_set())
