# 🏗️ Use Ubuntu base with Wine support
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 🧰 Install dependencies
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
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
        supervisor && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 👤 Create dedicated 'trader' user
RUN useradd -m -s /bin/bash trader

# ⚙️ Set working directory
WORKDIR /home/trader

# 🥂 Initialize Wine environment (ignore first-run warnings)
RUN wineboot --init || true

# 📦 Copy MT4 installer (make sure filename matches your real installer)
COPY --chown=trader:trader mt4setup.exe /home/trader/mt4setup.exe

# 🧩 Install MT4 silently (Wine GUI offscreen via xvfb)
RUN xvfb-run wine /home/trader/mt4setup.exe || true

# 🚀 Copy startup script inside trader folder
USER root
COPY --chown=trader:trader start.sh /home/trader/start.sh


# 👤 Switch back to 'trader' user
USER trader

# 🏁 Default working directory and command
WORKDIR /home/trader
ENTRYPOINT ["bash", "start.sh"]
