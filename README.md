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

## Configuration Files

## Performing Measurements
