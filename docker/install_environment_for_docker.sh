#!/bin/bash
ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime

set -e

if [ -f /etc/os-release ]; then
    . /etc/os-release
else
    echo "Error: Failed to obtain OS information."
    exit 1
fi

if [ "$ID" != "ubuntu" ]; then
    echo "Error: This script is for Ubuntu only. (Current OS: $ID)"
    exit 1
fi

if [ "$VERSION_ID" == "24.04" ]; then
    PYTHON_PKG="python3.12"
elif [ "$VERSION_ID" == "26.04" ]; then
    PYTHON_PKG="python3.14"
else
    echo "Error: Unsupported Ubuntu version. (Version: $VERSION_ID)"
    exit 1
fi

apt update -q
apt upgrade -y -q

apt install -y -q \
    curl \
    wget \
    gnupg \
    apt-transport-https \
    software-properties-common \
    libx11-xcb1 \
    libxkbfile1 \
    libsecret-1-0 \
    libgtk-3-0 \
    libnss3 \
    libxss1 \
    libasound2t64 \
    xdg-utils \
    unzip \
    git \
    build-essential \
    cmake \
    gdb \
    x11-apps \
    xvfb \
    clang-format \
    nano \
    ripgrep \
    pybind11-dev \
    fonts-noto-cjk \
    $PYTHON_PKG \
    ${PYTHON_PKG}-dev \
    ${PYTHON_PKG}-venv \
    python3-tk

# virtual environment setup
$PYTHON_PKG -m venv /opt/venv_python

/opt/venv_python/bin/pip install --upgrade pip
/opt/venv_python/bin/pip install --upgrade setuptools
/opt/venv_python/bin/pip install \
    numpy \
    scipy \
    control \
    matplotlib \
    mplcursors \
    plotly \
    dash \
    pytest \
    pandas \
    jupyter \
    openpyxl \
    sympy \
    astor \
    pybind11 \
    networkx \
    dill \
    requests \
    flask \
    kaleido \
    autopep8 

rm -rf /var/lib/apt/lists/*