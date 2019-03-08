#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import multiprocessing
import sys
from multiprocessing import Queue

import glob
import gzip
import logging
# pip install python-memcached
import memcache
import os
import time
from argparse import ArgumentParser
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
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


def send_data(memc_addr: str, queue: Queue, stop_value=None, *, dry_run: bool, timeout: int):
    if not dry_run:
        memc = memcache.Client([memc_addr], socket_timeout=timeout)
    while True:
        chunk_data = queue.get()
        if chunk_data is stop_value:
            break
        if dry_run:
            for key, ua in chunk_data.items():
                logging.debug("%s - %s -> %s" % (memc_addr, key, str(ua).replace("\n", " ")))
        else:
            set_multi(memc, chunk_data)
    if not dry_run:
        memc.disconnect_all()


def read_file(fn: str, device_memc: dict, send_memc_queus: Dict[str, Queue], chunk_size: int, dry_run: bool):
    logging.info('Processing %s' % fn)
    processed = errors = 0
    to_send_data = collections.defaultdict(dict)
    with gzip.open(fn) as fd:
        for line in fd:
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
                key, packed = result
                to_send_data[dev_type][key] = packed
                processed += 1

                # Continue if not enough data for chunk
                if len(to_send_data[dev_type]) != chunk_size:
                    continue

                send_memc_queus[dev_type].put(to_send_data[dev_type])
                del to_send_data[dev_type]
            else:
                errors += 1

    # Send remained data after closing a file.
    for dev_type, dev_type_data in to_send_data.items():
        send_memc_queus[dev_type].put(dev_type_data)

    if not dry_run:
        dot_rename(fn)
    return processed, errors


def create_send_queues_tasks(device_memc, options):
    thread_executor_sender = ThreadPoolExecutor()
    # Create necessary queue and start memc client threads for send data
    send_memc_queus = {}
    manager = multiprocessing.Manager()
    for name, addr in device_memc.items():
        q = manager.Queue()
        thread_executor_sender.submit(send_data, addr, q, stop_value=STOP_VALUE,
                                      dry_run=options.dry, timeout=options.timeout)
        send_memc_queus[name] = q

    return send_memc_queus, thread_executor_sender


def process_files(device_memc, send_memc_queus, options):
    """Run workers for parsing lines from files"""
    processes_count = options.worker_processes
    pool = multiprocessing.Pool(processes_count, maxtasksperchild=processes_count)
    all_processed = all_errors = 0

    mod_read_file = partial(read_file, device_memc=device_memc, send_memc_queus=send_memc_queus,
                            chunk_size=options.chunk_size, dry_run=options.dry)
    for processed, errors in pool.imap_unordered(mod_read_file, glob.iglob(options.pattern),
                                                 chunksize=processes_count * 10):
        all_processed += processed
        all_errors += errors

    return all_processed, all_errors


def run_threads_read_files(options, lines_queue):
    """Run threads for read files"""
    thread_executor_files = ThreadPoolExecutor(options.max_threads)
    for fn in glob.iglob(options.pattern):
        thread_executor_files.submit(read_file, fn, lines_queue, dry_run=options.dry)
    return thread_executor_files


def shutdown_script(thread_executor_sender, send_memc_queus):
    """Shutdown script gracefully"""
    for q in send_memc_queus.values():
        q.put((STOP_VALUE, STOP_VALUE))
    thread_executor_sender.shutdown()
    logging.info('All threads and processes has been stopped.')


def count_lines(processed_sum, errors_sum):
    """Count processed and error lines"""

    if processed_sum:
        err_rate = float(errors_sum) / processed_sum
        if err_rate < NORMAL_ERR_RATE:
            logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
        else:
            logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))
    logging.info('Script completed.')


def main(options):
    device_memc = {
        b"idfa": options.idfa,
        b"gaid": options.gaid,
        b"adid": options.adid,
        b"dvid": options.dvid,
    }

    send_memc_queus, thread_executor_sender = create_send_queues_tasks(device_memc, options)

    line_counters = process_files(device_memc, send_memc_queus, options)

    count_lines(*line_counters)

    shutdown_script(thread_executor_sender, send_memc_queus)


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
    parser.add_argument("--timeout", default=5)
    parser.add_argument("--dry", action="store_true", default=False)
    parser.add_argument("--pattern", default="/data/appsinstalled/*.tsv.gz")
    parser.add_argument("--idfa", default="127.0.0.1:33013")
    parser.add_argument("--gaid", default="127.0.0.1:33014")
    parser.add_argument("--adid", default="127.0.0.1:33015")
    parser.add_argument("--dvid", default="127.0.0.1:33016")

    cpu_count = multiprocessing.cpu_count()
    parser.add_argument("--worker_processes", type=int, default=cpu_count,
                        help='Number of process for parse lines')
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
