#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import time


class FPSMeter():
    def __init__(self, name='FPS', period=10.0):
        self.name = 'FPS for %s(PID-%d)' % (name, os.getpid())
        self.period = period
        self.last_time = time.time()
        self.count = 0.0
        self.total_count = 0
        self.dead_time = 0.0
        self.dead_time_clock = time.time()
        self._log = logging.getLogger("FPS_INFO")
        print('Initilized counter %s' % self.name)

    def increment(self, steps=1, before_str=''):
        self.count += steps
        self.total_count += steps
        current_time = time.time()
        if current_time - self.last_time > self.period:
            s = before_str + '%s is %0.2f' % (self.name, self.count /
                                              (current_time - self.last_time))
            if self.dead_time > 0:
                s += '(with %0.1f%% down time)' % (min(100, 100.0 * (
                    self.dead_time / (current_time - self.last_time))))
            print(s)
            self.count = 0
            self.last_time = current_time
            self.dead_time = 0
            self.dead_time_clock = current_time
            return True
        else:
            return False

    def now_passive(self):
        self.dead_time_clock = time.time()

    def now_active(self):
        self.dead_time += time.time() - self.dead_time_clock
