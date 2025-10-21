# Use Ubuntu 22.04 as base image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV JUPYTER_ENABLE_LAB=yes
ENV JUPYTER_TOKEN=""

# Set work directory
WORKDIR /workspace

# Update system and install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    build-essential \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI (detect architecture)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"; \
    elif [ "$ARCH" = "arm64" ]; then \
        curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws/

# Create a symlink for python (some packages expect 'python' command)
RUN ln -s /usr/bin/python3 /usr/bin/python

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Copy requirements file first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Install Jupyter and additional helpful packages
RUN pip install \
    jupyter \
    jupyterlab \
    notebook \
    ipywidgets \
    matplotlib \
    seaborn \
    pandas \
    numpy \
    boto3 \
    botocore

# Copy the entire project
COPY . .

# Create a non-root user for security
RUN useradd -m -s /bin/bash workshop && \
    chown -R workshop:workshop /workspace && \
    mkdir -p /home/workshop/.aws && \
    chown -R workshop:workshop /home/workshop/.aws

# Switch to non-root user
USER workshop

# Expose Jupyter port
EXPOSE 8888

# Set the default command to start Jupyter Lab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--NotebookApp.token=", "--NotebookApp.password="]