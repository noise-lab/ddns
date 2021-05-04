This repository describes and contains instructions for installing [a fork of dnscrypt-proxy](https://github.com/noise-lab/dnscrypt-proxy) that is capable of distributing queries across multiple recursive resolvers.
This enables clients to reduce the amount of queries that are centralized into recursive resolvers.
The proxy is capable of providing DNS resolution as a stub resolver on desktop devices, enabling all applications on a single device to benefit from distributing queries.
The proxy is also capable of providing DNS resolution as a DNS proxy on home routers, enabling all *devices* on a local network to distribute queries.

This repository also contains code for performing page load time measurements against the fork of dnscrypt-proxy, enabling users to understand the performance impact of distributed DNS resolution.
We provide instructions for performing these measurements from both desktop devices and home routers.

The repository is structured as follows:
- ...
- ...

## Installation and Running the Proxy
The proxy exists as a fork of dnscrypt-proxy, which we have tested on macOS and EdgeOS. To install the proxy and run it, we refer the reader to the instructions for the following operating systems:
- [MacOS](https://github.com/DNSCrypt/dnscrypt-proxy/wiki/Installation-macOS)
- [EdgeOS](https://github.com/DNSCrypt/dnscrypt-proxy/wiki/Installation-on-EdgeOS)

We note that the [upstream repository for dnscrypt-proxy](https://github.com/DNSCrypt/dnscrypt-proxy/wiki/Installation) has releases available for additional operating systems, and instructions for running the proxy on these operating systems. However, we have not tested our modifications on all of these operating systems.

## Configuration Files
To run the proxy, users must specify a configuration file. Such a file contains various options pertaining to how DNS resolution is performed by the proxy, such as which resolvers should be used, which protocols, and more. Our modifications to dnscrypt-proxy include additional options for specifying query distribution strategies. These strategies are as follows:

- Hash-based distribution: Second-level domain names (SLDs) are hashed to index into a list of resolvers, meaning that queries for the same SLD will always be sent to the same
resolver.
For example, all queries issued by a client for [google.com](google.com) and [images.google.com](images.google.com) will be sent
to the same resolver.
Furthermore, if the same client later queries [images.google.com](images.google.com), the query will be forwarded to the same resolver as before.
- Round-robin distribution: Using this strategy, queries are sequentially striped across a set of resolvers
R. The round-robin strategy results in each resolver would be assigned 1/R of the client's queries.

We have included [configuration files](https://github.com/noise-lab/multi-trr-public/src/config) for these distribution strategies. We have also included configuration files if users wish to send all of their queries to one of Cloudflare, Google, Quad9, or NextDNS' DoH servers. If users wish to modify our configuration files, they may consider the following options to be especially important:
- server_names: Specify a list of DNS resolvers to use, as defined by [this file](https://dnscrypt.info/public-servers).
- lb_strategy: Specify which load balancing strategy users wish to use on a per-query basis. Possible options are as follows:
    * `rr`: Distribute queries on a round-robin basis, as described above.
    * `hash`: Distribute queries by mapping SLDs to resolvers, as described above.
    * `random`: Distribute each query to a random resolver, as described above.
    * `p2`: Distribute queries by randomly choosing between the first two servers in server_names
    * `ph`: Distribute queries by randomly choosing between the top fastest half of servers in server_names
    * `first`: Send all queries to the first resolver in the list (i.e. the resolver that is alphanumerically sorted first). 
- lb_estimator: Specify whether to periodically estimate the latency to each recursive resolver, which is relevant for certain load balancing strategies. If clients wish to use the round-robin or hash strategies, they should set lb_estimator to `false`.
- query_log: Specify a log file to output queries received by the proxy
- log_file: Specify a log file for debugging/error messages
- log_level: Specify what kinds of messages should be logged to the file specified by log_file
- doh_servers: Specify whether DoH servers can be used.
- dnscrypt_servers: Specify whether DNSCrypt servers can be used.
- timeout: Specify a timeout for DNS queries, in milliseconds.

## Performing Measurements
We have created a Docker image that enables users to measure the impact of the proxy on page load times.
The Docker image is built to run on amd64 machines, but the Dockerfile that builds the image can be modified for different platforms.
The image is available [here](...).
You can load the image into Docker using `docker load < <image_name>.tar.gz`.

### Dependencies
Our code was built to run on Debian.
To build the DNS response time measurement tool, you will first need to install
the packages in the dns-timing/debs directory with `dpkg -i`.
You will also need to install the following dependencies:

* libcurl4-openssl-dev
* libssl-dev
* libev4, libev-dev
* libevent-2.1.6, libevent-core-2.1.6, libevent-openssl-2.1.6, libevent-dev
* libuv1

To instrument the Docker image to measure page loads, parse the resulting HARs,
and insert the HARs into a PostgreSQL database, you will need to install the
following dependencies:

* python3, python3-pip, python3-dev
* postgresql, postgresql-client
* dnsutils
* net-tools 
* autoconf
* automake
* build-essential
* libtool

Lastly, you will need to install the pip packages listed in 
src/measure/requirements.txt with the`pip3 install -r requirements.txt`

### Installation
Once you've installed the dependencies listed above, you need to do a few more
things before you can start some measurements:
* Create a PostgreSQL database and user that has write access to the database
* Modify the data/postgres.ini file to contain your PostgreSQL credentials. For
  the har_table field, choose the name of the table that you want to store HARs
  for page load times. For the dns_table field, choose the name of the table that
  you want to store DNS response times.
* Run the following script to initialize the tables in your database that will
  store HARs and DNS response times:
  `python3 database.py ../../data/postgres.ini`
* Run `make` in src/measure/dns-timing to create the DNS response time measurement tool

### Running a measurement
Assuming your credentials are in data/postgres.ini and you wish to measure the
websites listed in data/tranco_combined.txt, you can simply run `sudo ./measure.sh`
from the src/measure directory to start your measurements. We need `sudo` to 
measure the ping to recursive resolvers.

This script will perform page loads for each website in
data/tranco_combined.txt. These page loads will be performed using the random, round-robin, 
and hash distribution strategies. The configuration files we provided for the measurements 
use the DoH resolvers provided by Cloudflare, Google, Quad9, and NextDNS.
The script will also perform page loads by sending all queries to the DoH resolvers provided by 
Cloudflare, Google, Quad9, and NextDNS.


