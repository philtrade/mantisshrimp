# Choose the base image from to take.
# Using slim images is best practice
# This is for CUDA 10.1 
# For CUDA of other versions change the install torch line from pytorch source.
FROM ubuntu:18.04

# Install dependencies
# Do this first for caching
RUN apt-get update
RUN apt-get -y install gcc
RUN apt-get install -y git
RUN apt-get install -y python3.6
RUN apt-get install -y python3-pip
# RUN pip3 install git+git://github.com/lgvaz/mantisshrimp.git
RUN git clone https://github.com/lgvaz/mantisshrimp.git
WORKDIR "/mantisshrimp"

COPY requirements.txt  requirements.txt
COPY requirements-extra.txt requirements-extra.txt
RUN pip3 install torch==1.5.1+cu101 torchvision==0.6.1+cu101 -f https://download.pytorch.org/whl/torch_stable.html
RUN pip3 install -r requirements.txt
RUN pip3 install -r requirements-extra.txt
RUN pip3 .

# For Pycoco Tools
RUN pip3 install -U 'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI'

# COPY Important files
COPY mantisshrimp mantisshrimp
COPY examples examples
COPY samples samples
COPY tutorials tutorials

# We need to expose port an run a dummy output with wsgi server
