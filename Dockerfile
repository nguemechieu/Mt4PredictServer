# ===========================================================
#  MT4 AI Container — Headless Wine Environment for MetaTrader 4
#  Author: Noel Martial Nguemechieu
#  Purpose: Run MT4 Expert Advisor linked to PredictServer (AI bridge)
# ===========================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV WINEPREFIX=/home/trader/.wine
ENV DISPLAY=:0
ENV WINEDEBUG=-all

# --- Add 32-bit architecture + system deps ---
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y \
    software-properties-common wget gnupg2 ca-certificates \
    wine64 wine32 \
    xvfb x11vnc xdotool \
    unzip xdg-utils cabextract curl \
    net-tools supervisor \
    winbind fonts-wine cabextract \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Create non-root user for Wine isolation ---
RUN useradd -m trader && usermod -aG sudo trader
USER trader
WORKDIR /home/trader

# --- Initialize Wine environment ---
RUN wineboot --init || true

# --- Copy MT4 installer ---
# (Must exist in same folder as Dockerfile or mounted)
COPY mt4setup.exe /home/trader/

# --- Install MetaTrader 4 silently ---
# Note: some installers don’t support /S, so xvfb-run keeps it headless
RUN xvfb-run -a wine mt4_installer.exe /silent || true

# --- Shared volume for file exchange with AI PredictServer ---
VOLUME ["/home/trader/.wine/drive_c/MT4/MQL4/Files"]

# --- Copy custom startup script ---
COPY start.sh /home/trader/start.sh
RUN chmod +x /home/trader/start.sh

# --- Optional Wine settings (disable crash dialogs) ---
RUN echo "[wine]\n" > $WINEPREFIX/system.reg && \
    echo '"ShowCrashDialog"="0"' >> $WINEPREFIX/system.reg

# --- Health check to verify MT4 stays alive ---
HEALTHCHECK --interval=60s --timeout=5s \
  CMD pgrep wineserver || exit 1

# --- Run headless Xvfb + Wine MT4 ---
CMD ["xvfb-run", "-a", "/home/trader/start.sh"]
