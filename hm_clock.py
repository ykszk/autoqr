import datetime


class HMClock():
    '''
    Over midnight aware clock class
    '''
    def __init__(self, hour: int, minute: int):
        self.hour = hour
        self.minute = minute

    def __str__(self):
        return '{:02d}:{:02d}'.format(self.hour, self.minute)

    def __repr__(self):
        return 'HMClock({},{})'.format(self.hour, self.minute)

    def to_minute(self):
        return self.hour * 60 + self.minute

    def to_msec(self):
        return self.to_minute() * 60 * 1000

    @classmethod
    def from_str(cls, s: str):
        '''
        Create HMClock instance from hm string 'HH:MM'

        Args:
            s (str): 'HH:MM' string
        Returns:
            [hour:int, minute:int]
        '''
        if ':' in s:
            hm = [int(e) for e in s.split(':')]
        else:
            hm = int(s[:-2]), int(s[-2:])
        if hm[0] >= 24 or hm[0] < 0:
            raise ValueError('Invalid hour {}'.format(hm[0]))
        if hm[1] >= 60 or hm[1] < 0:
            raise ValueError('Invalid minute {}'.format(hm[1]))

        return HMClock(hm[0], hm[1])

    @classmethod
    def from_minute(cls, minute: int):
        if minute < 0:
            raise ValueError('Negative minute is invalid.')
        if minute > (24 * 60 - 1):
            raise ValueError('Input minute larger then 24 hour')

        h = minute // 60
        m = minute - h * 60
        return HMClock(h, m)

    @classmethod
    def now(cls):
        '''
        Create instance from current time
        '''
        n = datetime.datetime.now()
        return HMClock(n.hour, n.minute)

    def is_between(self, start: 'HMClock', end: 'HMClock'):
        start_m = start.to_minute()
        end_m = end.to_minute()
        self_m = self.to_minute()

        if start_m <= end_m:
            return start_m <= self_m < end_m
        else:
            return start_m <= self_m or self_m < end_m

    def delta(self, other: 'HMClock'):
        '''
        Over midnight aware delta.
        e.g. 23:00 - 6:00 = 7:00

        Returns:
            HMClock: other - self
        '''
        self_m = self.to_minute()
        other_m = other.to_minute()

        if self_m > other_m:
            other_m = other_m + 24 * 60

        return HMClock.from_minute(other_m - self_m)

    def __eq__(self, other: 'HMClock'):
        if not isinstance(other, HMClock):
            return NotImplemented
        return self.hour == other.hour and self.minute == other.minute

    def __lt__(self, other: 'HMClock'):
        if not isinstance(other, HMClock):
            return NotImplemented
        self_m = self.to_minute()
        other_m = other.to_minute()
        return self_m < other_m

    def __ne__(self, other: 'HMClock'):
        return not self.__eq__(other)

    def __le__(self, other: 'HMClock'):
        return self.__lt__(other) or self.__eq__(other)

    def __gt__(self, other: 'HMClock'):
        return not self.__le__(other)

    def __ge__(self, other: 'HMClock'):
        return not self.__lt__(other)

    def __sub__(self, other: 'HMClock'):
        if not isinstance(other, HMClock):
            return NotImplemented
        return other.delta(self)
