#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os.path
import sys
import time
import subprocess
import shutil

from datetime import datetime
from enum import Enum

from selenium import webdriver
from selenium.webdriver.firefox.options import Options


def main():
    # Parse the command line arguments
    models = ['hash', 'rr', 'random', 'cloudflare', 'google', 'quad9', 'nextdns']
    parser = argparse.ArgumentParser()
    parser.add_argument('website')
    parser.add_argument('dns_type', choices=['dns', 'doh', 'dot', 'dnscrypt-proxy_doh'])
    parser.add_argument('trr_resolver_ip')
    parser.add_argument('trr_resolver_uri')
    parser.add_argument('model', choices=models)
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()

    dnscrypt_config_file = '/dnscrypt-proxy/dnscrypt-proxy/dnscrypt-proxy-{0}.toml'.format(args.model)

    # Enable devtools in Firefox
    options = Options()
    options.headless = True
    options.add_argument('-devtools')

    # Enable the netmonitor toolbox in devtools so we can save HARs
    profile = webdriver.FirefoxProfile()
    profile.set_preference('devtools.toolbox.selectedTool', 'netmonitor')

    # Set up DNS configuration
    subprocess.run(["sudo", "cp", "/etc/resolv.conf", "/etc/resolv.upstream.conf"])
    subprocess.run(["sudo", "cp", "resolv.conf", "/etc/resolv.conf"])
    if args.dns_type == 'dnscrypt-proxy_doh':
        subprocess.run("sudo /dnscrypt-proxy/dnscrypt-proxy/dnscrypt-proxy -config {0} &> /dev/null &".format(dnscrypt_config_file), shell=True)
        subprocess.run(["sudo", "sleep", "5s"])

    # Configure the DNS settings in Firefox
    if args.dns_type == 'dns' or args.dns_type == 'dot' or args.dns_type == 'dnscrypt-proxy_doh':
        options.set_preference('network.trr.mode', 0)
    elif args.dns_type == 'doh':
        options.set_preference('network.trr.mode', 3)
        options.set_preference('network.trr.request-timeout', 1500)
        options.set_preference('network.trr.max-fails', 5)
        trr_resolver_ip = args.trr_resolver_ip
        trr_resolver_uri = args.trr_resolver_uri
        if trr_resolver_ip:
            options.set_preference('network.trr.bootstrapAddress', trr_resolver_ip)
        if trr_resolver_uri:
            options.set_preference('network.trr.uri', trr_resolver_uri)

    # Launch Firefox and install our extension for getting HARs
    driver = webdriver.Firefox(options=options,
                               firefox_profile=profile,
                               firefox_binary="/opt/firefox/firefox-bin")
    driver.install_addon("/home/seluser/measure/harexporttrigger-0.6.2-fx.xpi")
    driver.set_page_load_timeout(args.timeout)

    # Make a page load
    started = datetime.now()
    driver.get(args.website)

    # Once the HAR is on disk in the container, write it to stdout so the host machine can get it
    har_file = "/home/seluser/measure/har.json"
    def har_file_ready():
        return os.path.exists(har_file + ".ready")

    while (datetime.now() - started).total_seconds() < args.timeout \
            and not har_file_ready():
        time.sleep(1)

    if har_file_ready():
        with open(har_file, 'rb') as f:
            sys.stdout.buffer.write(f.read())
    driver.quit()


if __name__ == '__main__':
    main()
