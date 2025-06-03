FROM python:3.12-slim

# Install common packages and sudo
RUN apt-get update && apt-get install -y \
    sudo \
    git \
    curl \
    wget \
    vim \
    nano \
    htop \
    procps \
    iputils-ping \
    dnsutils \
    openssh-client \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install gh \
    && rm -rf /var/lib/apt/lists/*

# Create tinker user with home directory as /home/tinker
RUN groupadd -g 1000 tinker && \
    useradd -u 1000 -g 1000 -d /home/tinker -m -s /bin/bash tinker && \
    echo "tinker ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to tinker user
USER tinker

# Set working directory to home
WORKDIR /home/tinker

# Set environment variables
ENV HOME=/home/tinker
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Keep container running
CMD ["tail", "-f", "/dev/null"]
