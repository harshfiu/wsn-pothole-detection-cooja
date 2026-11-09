#!/bin/bash
# Installs Contiki 3.0, Cooja and the browser demo tools on Ubuntu 20.04 (WSL or native).
# On Windows, first run:  wsl --install -d Ubuntu-20.04
# Then, as root inside that distro:  bash setup_wsl.sh
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq build-essential gcc-msp430 binutils-msp430 msp430-libc msp430mcu \
  openjdk-8-jdk ant git python3 net-tools libncurses5-dev libxtst6 libxi6 libxrender1 \
  fontconfig fonts-dejavu xvfb xdotool imagemagick x11-utils x11vnc novnc websockify openbox
update-alternatives --set java /usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java
update-alternatives --set javac /usr/lib/jvm/java-8-openjdk-amd64/bin/javac

id wsn >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo wsn
echo 'wsn ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/wsn
chmod 440 /etc/sudoers.d/wsn
printf '[user]\ndefault=wsn\n' > /etc/wsl.conf

su - wsn -c '
set -e
cd ~
[ -d contiki ] || git clone -q https://github.com/contiki-os/contiki.git
cd contiki
git checkout -q 3.0 || git checkout -q release-3-0
git submodule update --init --recursive -q
cd tools/cooja
ant jar 2>&1 | tail -3
'
echo "Done. Next, as user wsn, from this repo: bash sync.sh"
