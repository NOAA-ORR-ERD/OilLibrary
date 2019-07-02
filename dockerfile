FROM gitlab.orr.noaa.gov:5002/centos:latest

RUN yum update -y
# RUN yum install -y gcc

COPY ./ /oillibrary/
# RUN cd /oillibrary/ && pip install -r requirements.txt
# RUN conda install scipy
# RUN cd /oillibrary/ && python setup.py develop
