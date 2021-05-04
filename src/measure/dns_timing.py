import os
import subprocess
import logging.config
import tldextract

log = logging.getLogger('postgres')


def create_resolver_map(all_domains, dnsmasq_conf_file, default_resolver):
    dnsmasq_conf = {}
    with open(dnsmasq_conf_file, 'r') as f:
        lines = f.read().splitlines()

    for line in lines:
        if not line.startswith('server='):
            continue
        line = line.split('/')
        domain = line[1]
        resolver = line[2]
        if resolver == '#':
            resolver = default_resolver
        dnsmasq_conf[domain] = resolver

    resolver_map = {}
    for domain in all_domains:
        if domain not in dnsmasq_conf:
            resolver = default_resolver
        else:
            resolver = dnsmasq_conf[domain]

        if resolver not in resolver_map:
            resolver_map[resolver] = [domain]
        else:
            resolver_map[resolver].append(domain)
    return resolver_map


def measure_dns(website, har, har_uuid, dns_type, default_resolver_ip,
                default_resolver_uri, model):
    unique_domains = get_unique_domains(har)
    dnsmasq_conf_file = '../docker/dnsmasq_{0}.conf'.format(model)
    dnsmasq_map = create_resolver_map(unique_domains, dnsmasq_conf_file,
                                      default_resolver_ip)

    try:
        all_dns_info = {}
        for resolver_ip in dnsmasq_map:
            domains = dnsmasq_map[resolver_ip]
            domains_filename = "domains-" + str(har_uuid) + ".txt"
            write_domains(domains, domains_filename)

            if dns_type == 'dns':
                dns_opt = 'do53'
            #     resolver = resolver_ip
            # elif dns_type == 'dot':
            #     dns_opt = 'dot'
            #     resolver = resolver_ip
            # elif dns_type == 'doh':
            #     dns_opt = 'doh'
            #     resolver = resolver_uri

            cmd = ["dns-timing/dns-timing", dns_opt,
                   resolver_ip, domains_filename]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            output = output.decode('utf-8')
            dns_info = parse_output(output, website, domains, resolver_ip)
            all_dns_info[resolver_ip] = dns_info
            os.remove(domains_filename)
        return all_dns_info
    except Exception as e:
        log.error(e)
        err = 'Error getting DNS timings: website {0}, dns_type {1}, ' \
                'default_resolver_ip {2}, default_resolver_uri {3}'
        os.remove(domains_filename)
        log.error(err.format(website, dns_type, default_resolver_ip, default_resolver_uri))
    return None


def parse_output(output, website, domains, resolver):
    # Initialize the dict with all domains in the HAR
    all_dns_info = {}
    for domain in domains:
        all_dns_info[domain] = {'response_time': 0.,
                                'response_size': 0,
                                'error': 0}

    # If there's no output from the DNS tool, return immediately
    if not output:
        return all_dns_info

    # For each domain in the HAR, record DNS response time and size
    try:
        lines = output.splitlines()
        for line in lines:
            status, domain, response_time, size_or_error = line.split(',', 4)
            if status == "ok":
                response_size = int(size_or_error)
                error = None
            else:
                response_size = None
                error = int(size_or_error)

            all_dns_info[domain] = {'response_time': float(response_time),
                                    'response_size': response_size,
                                    'error': error,
                                    'recursive': resolver}
    except Exception as e:
        err = 'Error parsing DNS output for website {0}: {1}'
        log.error(err.format(website, e))
    return all_dns_info


def get_unique_domains(har):
    if not har:
        return []

    if "entries" not in har:
        return []
    entries = har["entries"]

    if len(entries) == 1:
        return []

    domains = []
    for entry in entries:
        # If a DNS request was made, record the timings
        if "request" not in entry:
            continue
        request = entry["request"]

        if "url" not in request:
            continue
        url = request["url"]

        ext = tldextract.extract(url)
        if ext.subdomain:
            fqdn = ext.subdomain + "." + ext.domain + "." + ext.suffix
        else:
            fqdn = ext.domain + "." + ext.suffix
        domains.append(fqdn)
    return list(set(domains))


def write_domains(domains, domains_filename):
    with open(domains_filename, "w") as f:
        for d in domains:
            f.write("{0}\n".format(d))
