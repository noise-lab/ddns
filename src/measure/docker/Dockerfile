FROM debian:testing-slim

ENV DEBIAN_FRONTEND noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN true

RUN apt-get -y update && \
    apt-get -y install --no-install-recommends \
        sudo python3-pip vim wget bzip2 libgtk-3-0 libdbus-glib-1-2 \
        libxt6 procps dnsutils libssl-dev openssl libyaml-dev git \
        libtool m4 autoconf build-essential automake libx11-xcb-dev golang-go gcc

RUN wget -q https://ftp.mozilla.org/pub/firefox/releases/84.0.1/linux-x86_64/en-US/firefox-84.0.1.tar.bz2 -O /tmp/firefox.tar.bz2  && \
    tar -xf /tmp/firefox.tar.bz2 -C /opt/ && \
    rm /tmp/firefox.tar.bz2

RUN wget -q https://github.com/mozilla/geckodriver/releases/download/v0.28.0/geckodriver-v0.28.0-linux64.tar.gz -O /tmp/geckodriver.tar.gz && \
    tar -xf /tmp/geckodriver.tar.gz -C /usr/local/bin/ && \
    rm /tmp/geckodriver.tar.gz

RUN git clone https://github.com/noise-lab/dnscrypt-proxy.git && \
    cd dnscrypt-proxy/dnscrypt-proxy && \
    go build -ldflags="-s -w" -mod vendor

ADD requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

RUN mkdir -p /usr/lib/mozilla/native-messaging-hosts/
ADD har_catcher.json /usr/lib/mozilla/native-messaging-hosts/

RUN useradd -ms /bin/bash seluser
RUN adduser seluser sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

ADD harexporttrigger-0.6.2-fx.xpi \
    run.py \
    har_catcher.py \
    resolv.conf \
    /home/seluser/measure/

ADD dnscrypt-proxy-hash.toml \
    dnscrypt-proxy-rr.toml \
    dnscrypt-proxy-random.toml \
    dnscrypt-proxy-cloudflare.toml \
    dnscrypt-proxy-google.toml \
    dnscrypt-proxy-quad9.toml \
    dnscrypt-proxy-nextdns.toml \
    /dnscrypt-proxy/dnscrypt-proxy/

RUN chown seluser:seluser -R /home/seluser/measure

USER seluser
WORKDIR /home/seluser/measure

ENTRYPOINT ["sudo", "python3", "/home/seluser/measure/run.py"]
