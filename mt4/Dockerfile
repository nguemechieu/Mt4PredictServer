# Use Ubuntu base with Wine support
FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y \
    software-properties-common \
    wget \
    gnupg2 \
    ca-certificates \
    wine64 \
    wine32 \
    xvfb \
    x11vnc \
    unzip \
    xdg-utils \
    curl \
    cabextract \
    net-tools \
    supervisor \
    && apt-get clean

# Create wine user
RUN useradd -m trader
USER trader
WORKDIR /home/trader

# Setup Wine
RUN wineboot --init || true

# Copy your MT4 installer (assumes you have a terminal.exe or installer.exe)
COPY mt4_installer.exe /home/trader/

# Install MT4 (silent if possible)
RUN xvfb-run wine mt4_installer.exe || true

# Optional: configure Wine and start script
COPY start.sh /home/trader/
RUN chmod +x /home/trader/start.sh

CMD ["xvfb-run", "/home/trader/start.sh"]
