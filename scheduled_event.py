from threading import Event, Thread
from typing import List, Tuple
from collections import namedtuple
import time
import datetime

from logzero import logger as default_logger

from utils import log_call
from hm_clock import HMClock

Period = namedtuple('Period', ['start', 'end'])


class Periods():
    def __init__(self, periods: List[Tuple[str, str]]):
        self.periods = [
            Period(HMClock.from_str(p[0]), HMClock.from_str(p[1]))
            for p in periods
        ]
        self.periods.sort(key=lambda p: p.start)
        self._validate_periods()

    def _validate_periods(self):
        if len(self.periods) == 1:
            return  # skip validation
        for i in range(len(self.periods)):
            if self.periods[i].start.is_between(self.periods[i - 1].start,
                                                self.periods[i - 1].end):
                raise RuntimeError('Overlapping periods: {}'.format(
                    self.periods))

    def between(self, clock: 'HMClock'):
        '''
        Return current period
        '''
        for p in self.periods:
            if clock.is_between(p.start, p.end):
                return p
        return None

    def next(self, clock: 'HMClock'):
        '''
        Return next period for the clock's time
        '''
        deltas = [(p, (p.start - clock).to_minute()) for p in self.periods]
        deltas = [(p, d) if d > 0 else (p, d + 24 * 60) for p, d in deltas]
        deltas.sort(key=lambda d: d[1])
        return deltas[0][0]

    def __eq__(self, other: 'Periods'):
        return self.periods == other.periods


class ScheduledEvent():
    def __init__(self, periods: List[Tuple[str, str]], logger=None):
        '''
        Args:
            periods (list[('start', 'end')]): Execution periods
        '''
        self.logger = logger or default_logger
        self.periods = Periods(periods)
        self.logger.debug('Init ScheduledEvent: %s', self.periods)
        self._enabled = False
        self.event = Event()
        self.event.clear()
        self.interval = 1

        self.thread = Thread(target=self._loop)
        self.thread.daemon = True
        self.thread.start()

    def _loop(self):
        while True:
            self.update()
            time.sleep(self.interval)

    def update(self):
        if self.periods.between(HMClock.now()) is not None:
            if not self.event.is_set() and self._enabled:
                self.logger.info('Set event')
                self.event.set()
        else:
            if self.event.is_set():
                self.logger.info('Clear event')
                self.event.clear()

    def start(self):
        self._enabled = True
        self.update()

    def stop(self):
        self._enabled = False
        self.event.clear()
