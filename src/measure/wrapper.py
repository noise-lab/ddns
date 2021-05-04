#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import enum
import itertools
import json
import logging.config
import random
import re
import subprocess
import time
import uuid

from database import DNSDatabase
from ping_util import ping_resolver
from response_size import get_dns_sizes, get_doh_sizes
from dns_timing import measure_dns


class Resolvers(enum.Enum):
    default = (None, None)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('database_config_file')
    parser.add_argument('website_list')
    parser.add_argument('log_config_file')
    parser.add_argument('experiment')
    parser.add_argument('start_index', type=int)
    parser.add_argument('stop_index', type=int)
    parser.add_argument('cdn', choices=['None', 'cloudflare', 'google', 'multicdn'])
    args = parser.parse_args()

    # Set up a logger
    logging.config.fileConfig(args.log_config_file)
    logging.basicConfig(filename='measurement.log', level=logging.DEBUG)
    log = logging.getLogger('wrapper')

    # Load the list of websites to measure from disk
    websites = load_websites(args.website_list)
    websites_subset = websites[args.start_index:args.stop_index]

    # Connect to the database for storing HARs
    db = DNSDatabase.init_from_config_file(args.database_config_file)
    
    # Run the measurements
    log.info("Starting new run through ALL configurations")
    start_time = time.time()
    start_ifconfig = "start_ifconfig_{0}.txt".format(args.experiment)
    save_ifconfig(start_ifconfig)

    run(log, db, args.experiment, websites_subset, args.cdn)

    end_time = time.time()
    end_ifconfig = "end_ifconfig_{0}.txt".format(args.experiment)
    save_ifconfig(end_ifconfig)
    log.info("elapsed time: %f seconds", end_time - start_time)


def save_ifconfig(filename):
    ifconfig = subprocess.check_output(["/sbin/ifconfig"])
    ifconfig = ifconfig.decode("utf-8")
    with open(filename, "w") as f:
        f.write(ifconfig)


def get_default_nameservers():
    # Parse the name servers from /etc/resolv.conf
    nameservers = []
    with open("/etc/resolv.conf") as f:
        for line in f:
            if line.startswith("nameserver "):
                _, nameserver = line.split(" ", 1)
                nameserver = nameserver[:-1]
                nameservers.append(nameserver)
    return nameservers[0]


def run(log, db, experiment, websites, cdn):
    dns_options = ['dnscrypt-proxy_doh']
    recursive_options = ['default']
    # cloudflare_models = ['cloudflare_random', 'cloudflare_cdn', 'cloudflare_default']
    # google_models = ['google_random', 'google_cdn', 'google_default']
    # multicdn_models = ['cf_google_multicdn']

    # Depending on which CDN websites we're measuring, choose models
    # if cdn == 'cloudflare':
    #     models = cloudflare_models
    # elif cdn == 'google':
    #     models = google_models
    # elif cdn == 'multicdn':
    #     models = multicdn_models
    # else:
    #     raise Exception('Must specify a valid CDN')
    
    models = ['hash', 'rr', 'random', 'cloudflare', 'google', 'quad9', 'nextdns']

    # Shuffle the configurations for measurements we want to run
    options = list(itertools.product(recursive_options, dns_options, models))

    random.shuffle(websites)
    for website in websites:
        random.shuffle(options)
        for recursive, dns_type, model in options:
            if recursive == 'default' and dns_type in ('doh', 'dot'):
                continue
            run_configuration(log, db, experiment, website, recursive,
                              dns_type, model)


def run_configuration(log, db, experiment, website, recursive,
                      dns_type, model):
    # Run a measurment for a single website for a given configuration
    resolver_ip = None
    resolver_uri = None
    if recursive == "default":
        resolver_ip = get_default_nameservers()
    else:
        resolver_ip, resolver_uri = Resolvers[recursive].value

    # Collect a HAR, ping time to resolver, and
    # bytes sent/received for a DNS query
    log.info('Collecting {} {} {} for {}'.format(recursive, dns_type, model, website))
    try:
        har, har_uuid, har_error, delays, all_dns_info = \
            measure_and_collect_har(log, website, resolver_ip, resolver_uri, dns_type, model)

        # Insert HAR, ping times, and DNS timings into the db
        rv_har = db.insert_har(experiment, website, recursive,
                               dns_type, model, har, har_uuid, har_error, delays)
        rv_har = None
        if not rv_har:
            msg = "Saved HAR for website {}, config: {}, {}, {}"
            log.info(msg.format(website, recursive, dns_type, model))
            log.info("Delays for website {}: {}".format(website, delays))
            if all_dns_info:
                # rv_dns = db.insert_dns(har_uuid, experiment, recursive,
                #                        dns_type, model, all_dns_info)
                rv_dns = None
                if not rv_dns:
                    msg = "Saved DNS timings for website {}"
                    log.info(msg.format(website))
    except Exception as e:
        log.error("Unknown error for website {}: {}".format(website, e))


def measure_and_collect_har(log, website, resolver_ip, resolver_uri,
                            dns_type, model):
    # Get a HAR for a website
    website = 'https://{0}'.format(website)
    if dns_type == 'dns' or dns_type == 'dnscrypt-proxy_doh':
        dns_opt = "--dns={0}".format(resolver_ip)
        cmd = ['docker', 'run', dns_opt, '--rm', '--cap-add=NET_ADMIN',
                'multitrr-test:latest', website, dns_type, 'n/a', 'n/a',
               model]
    else:
        cmd = ['docker', 'run', '--rm', '--cap-add=NET_ADMIN',
                'multitrr-trr:latest', website, dns_type, resolver_ip, resolver_uri,
               model]

    # Check if HAR is empty
    try:
        run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        log.error('Error in container for {}:\n{}'.format(website, e.output))
        har = None

    # Decode the output
    try:
        har = run.stdout.decode('utf-8')
        har_error = None
    except Exception as e:
        log.error('Error decoding output for website {}: {}'.format(website, e))
        har_error = run.stderr.decode('utf-8')
        har = None

    # Check if the output is empty
    if not har or har == " ":
        log.error('Output is empty for website: {}'.format(website))
        har = None
        har_error = run.stderr.decode('utf-8')
        json_har = None
    else:
        # Load the HAR as a JSON
        try:
            json_har = json.loads(har)
            for entry in json_har['entries']:
                if 'text' in entry['response']['content']:
                   del entry['response']['content']['text']
            # If zero-bytes remain after stripping content, we remove them.
            # We are removing zero bytes from the JSON file even though they are
            # technically correct because we don't care for the places they can
            # occur and PostgreSQL chokes on them.
            har_reassembled = json.dumps(json_har)
            if "\\u0000" in har_reassembled:
                har_stripped = re.sub(r"(\\)+u0000", "", har_reassembled)
                json_har = json.loads(har_stripped)
        except Exception as e:
            log.error('Error decoding HAR for website: {}\n'.format(website))
            har_error = str(e)
            json_har = None

    # Ping the resolver 5 times
    try:
        cloudflare_delays = ping_resolver('dns.cloudflare.com', count=5)
        google_delays = ping_resolver('dns.google', count=5)
        quad9_delays = ping_resolver('dns9.quad9.net', count=5)
        nextdns_delays = ping_resolver('dns.nextdns.io', count=5)
        # opendns_delays = ping_resolver('208.67.222.222', count=5)
        # default_delays = ping_resolver(resolver_ip, count=5)
        delays = {
                   'dns.cloudflare.com': cloudflare_delays, 
                   'dns.google': google_delays,
                   'dns9.quad9.net': quad9_delays,
                   'dns.nextdns.io': nextdns_delays
                   # resolver_ip: default_delays, 
                   # '208.67.222.222': opendns_delays}
                 }
    except:
        log.error('Error pinging resolver: {0}\n'.format(resolver_ip))
        delays = {}
    
    # Create a UUID for the HAR
    har_uuid = uuid.uuid1()

    # Get DNS resolution times for each unique domain in HAR
    try:
        if json_har:
            # all_dns_info = measure_dns(website, json_har, har_uuid, dns_type,
            #                            resolver_ip, resolver_uri, model)
            all_dns_info = None
        else:
            all_dns_info = None
    except Exception as e:
        log.error('Error getting DNS timings:', str(e))
        all_dns_info = None
    return json_har, har_uuid, har_error, delays, all_dns_info


def load_websites(f):
    with open(f, 'r') as ftr:
        websites = [line.strip() for line in ftr]
    return websites


if __name__ == '__main__':
    main()
