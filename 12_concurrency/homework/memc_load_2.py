#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import multiprocessing
import sys
import time

import glob
import gzip
import logging
# pip install python-memcached
import memcache
import multiprocessing.pool
import os
from argparse import ArgumentParser
from concurrent.futures.thread import ThreadPoolExecutor
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
from multiprocessing import Queue
from typing import Dict

import appsinstalled_pb2

NORMAL_ERR_RATE = 0.01
STOP_VALUE = None
AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def prepare_appsinstalled(appsinstalled):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    return key, packed


def parse_appsinstalled(line):
    line_parts = line.strip().split(b"\t")
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(b",")]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
        logging.info("Not all user apps are digits: `%s`" % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info("Invalid geo coords: `%s`" % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def worker(lines_queue: Queue, device_memc: dict, send_memc_queus: Dict[str, Queue], stop_value=None, *,
           counter_queue: Queue):
    logging.info(f'PID for worker is {os.getpid()}')
    processed = errors = 0
    while True:
        line = lines_queue.get()
        if line is stop_value:
            break
        line = line.strip()
        if not line:
            continue
        appsinstalled = parse_appsinstalled(line)
        if not appsinstalled:
            errors += 1
            continue
        dev_type = appsinstalled.dev_type
        memc_addr = device_memc.get(dev_type)
        if not memc_addr:
            errors += 1
            logging.error("Unknow device type: %s" % appsinstalled.dev_type)
            continue
        result = prepare_appsinstalled(appsinstalled)
        if result:
            send_memc_queus[dev_type].put(result)
            processed += 1
        else:
            errors += 1
    counter_queue.put((errors, processed))
    # exit(0)


def set_multi(memc, data, retry_count=3, retry_timeout=1):
    for _ in range(retry_count):
        r = memc.set_multi(data)
        if r:
            # Вернулись какие-то значения, значит строки не были добавлены. Повторяем через таймаут
            time.sleep(retry_timeout)
            continue
        else:
            logging.debug('Successfully sent data to memc.')
            return
    raise Exception(f'Cant\'t added data into memc {memc}')


def send_data(memc_addr: str, queue: Queue, chunk_size: int, stop_value=None, *, dry_run: bool):
    if not dry_run:
        memc = memcache.Client([memc_addr])
    n = 0
    data = {}
    while True:
        n += 1
        key, ua = queue.get()
        if not (n % chunk_size) or key is stop_value:
            if dry_run:
                for key, ua in data.items():
                    logging.debug("%s - %s -> %s" % (memc_addr, key, str(ua).replace("\n", " ")))
            else:
                set_multi(memc, data)
            data = {}

        if key is stop_value:
            break
        data[key] = ua
    if not dry_run:
        memc.disconnect_all()


def read_file(fn: str, queue: Queue, *, dry_run: bool):
    logging.info('Processing %s' % fn)
    with gzip.open(fn) as fd:
        for line in fd:
            queue.put(line)
    if not dry_run:
        dot_rename(fn)


def main(options):
    device_memc = {
        b"idfa": options.idfa,
        b"gaid": options.gaid,
        b"adid": options.adid,
        b"dvid": options.dvid,
    }

    thread_executor_sender = ThreadPoolExecutor()
    # Create necessary queues and start memc client threads for send data
    send_memc_queus = {}
    for name, addr in device_memc.items():
        q = multiprocessing.Queue()
        thread_executor_sender.submit(send_data, addr, q, options.chunk_size, stop_value=STOP_VALUE,
                                      dry_run=options.dry)
        send_memc_queus[name] = q

    lines_queue = multiprocessing.Queue()
    counter_queue = multiprocessing.Queue()

    # Run workers for parsing lines
    process_number = options.worker_processes
    kwds = {
        "stop_value": STOP_VALUE,
        "counter_queue": counter_queue,
    }
    args = (lines_queue, device_memc, send_memc_queus)
    processes = []
    for _ in range(process_number):
        p = multiprocessing.Process(target=worker, args=args, kwargs=kwds)
        p.start()
        processes.append(p)

    # Run threads for read files
    thread_executor_files = ThreadPoolExecutor(options.max_threads)
    for fn in glob.iglob(options.pattern):
        thread_executor_files.submit(read_file, fn, lines_queue, dry_run=options.dry)

    # Shutdown script gracefully
    thread_executor_files.shutdown()
    for _ in range(process_number):
        lines_queue.put(STOP_VALUE)
    for p in processes:
        p.join()
    for q in send_memc_queus.values():
        q.put((STOP_VALUE, STOP_VALUE))
    thread_executor_sender.shutdown()

    # Count processed and error lines
    errors_sum = processed_sum = 0
    for _ in range(process_number):
        errors, processed = counter_queue.get()
        errors_sum += errors
        processed_sum += processed
    if processed_sum:
        err_rate = float(errors_sum) / processed_sum
        if err_rate < NORMAL_ERR_RATE:
            logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
        else:
            logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))
    logging.info('Script completed.')


def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split(b"\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-t", "--test", action="store_true", default=False)
    parser.add_argument("-l", "--log", default=None)
    parser.add_argument("--dry", action="store_true", default=False)
    parser.add_argument("--pattern", default="/data/appsinstalled/*.tsv.gz")
    parser.add_argument("--idfa", default="127.0.0.1:33013")
    parser.add_argument("--gaid", default="127.0.0.1:33014")
    parser.add_argument("--adid", default="127.0.0.1:33015")
    parser.add_argument("--dvid", default="127.0.0.1:33016")

    cpu_count = multiprocessing.cpu_count()
    parser.add_argument("--worker_processes", type=int, default=cpu_count,
                        help='Number of process for parse lines')
    parser.add_argument("--max_threads", type=int, default=cpu_count * 5,
                        help='Number of threads for read files and send data to memcached. '
                             'Default cpu_count *5 as python docs recommendation for threads executor')
    parser.add_argument("--chunk_size", type=int, default=1024, help='Chunk size to send data into memcached')

    args = parser.parse_args()
    logging.basicConfig(filename=args.log, level=logging.INFO if not args.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if args.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % args)
    try:
        main(args)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
