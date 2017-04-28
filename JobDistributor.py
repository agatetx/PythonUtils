import os
import time
from collections import defaultdict, deque
from multiprocessing import Process, Queue
from threading import Lock, Thread
from FPSMeter import FPSMeter


class ThreadSafeCounter():
    def __init__(self):
        self.lock = Lock()
        self.counter = -1

    def increment(self):
        with self.lock:
            self.counter += 1
            return self.counter


def worker(q_in, q_out, SlaveClass, params):
    slave = SlaveClass(*params)    
    while True:
        job_id, metadata, data = q_in.get()
        res = slave.detect(data)
        q_out.put((job_id, metadata, res))


def result_sync_worker(q_in, q_out):
    wavefront = -1
    stack = dict()
    meter = FPSMeter('JobDitributor', period=10)
    while True:
        job_id, metadata, res = q_in.get()
        stack[job_id] = (metadata, res)
        while (wavefront + 1) in stack:
            wavefront = wavefront + 1
            q_out.put(stack[wavefront])
            meter.increment()
            #print(wavefront)
            del stack[wavefront]


def poll_dq(dq):
    while True:
        try:
            return dq.popleft()
        except IndexError:
            time.sleep(0.01)


def input_worker(procs, dq_in, counter):
    prev_data = poll_dq(dq_in)
    #print('----------',len(dq_in))
    while True:
        for proc_ind in procs:
            if procs[proc_ind]['queue'].empty():
                #print('----------',len(dq_in))
                procs[proc_ind]['queue'].put((counter.increment(),
                                              prev_data[0], prev_data[1]))
                #print(counter.counter)
                prev_data = poll_dq(dq_in)


class JobDistributor():
    def __init__(self,
                 q_out_synced,
                 n_procs,
                 SlaveClass,
                 params=(),
                 queue_size=None):
        self.n_procs = n_procs
        self.dq_in = deque(maxlen=queue_size)
        self.q_out = Queue()
        self.procs = defaultdict(dict)
        self.job_counter = ThreadSafeCounter()

        for ii in range(int(self.n_procs)):
            self.procs[ii]['queue'] = Queue(maxsize=1)
            p = Process(
                target=worker,
                args=(self.procs[ii]['queue'], self.q_out, SlaveClass, params),
                daemon=True)
            p.start()
            self.procs[ii]['proc'] = p

        t = Thread(
            target=input_worker,
            args=(self.procs, self.dq_in, self.job_counter),
            daemon=True)
        t.start()

        sync_worker = Process(
            target=result_sync_worker, args=(self.q_out, q_out_synced))
        sync_worker.daemon = True
        sync_worker.start()

    def push(self, data, metadata=[]):
        self.dq_in.append((metadata, data))


if __name__ == '__main__':
    # Happy usage example
    import numpy as np

    class Friend():
        def __init__(self):
            pass

        def detect(self, data):
            time.sleep(np.random.uniform(10) / 30)  # processing time
            return data**2

    results_queue = Queue()
    distributor = JobDistributor(results_queue, 10, Friend, queue_size=10)
    for ii in range(100):
        distributor.push(ii)
        time.sleep(0.001)

    while True:
        print(results_queue.get())
