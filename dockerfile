FROM registry.orr.noaa.gov/erd/centos-conda/centos7-python3

RUN yum update -y
# RUN yum install -y gcc

RUN conda info

COPY ./ /OilLibrary/
RUN cd /OilLibrary/ && conda install -y --file conda_requirements_py3.txt

# RUN cd /OilLibrary/ && pip install -r requirements.txt
# RUN conda install scipy

RUN cd /OilLibrary/ && python setup.py develop


