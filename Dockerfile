FROM python:3.7-slim
MAINTAINER leon@cornelissensolutions.nl

RUN apt-get update && apt-get install -y \
    git \
    python3-pip

COPY ./Requirements.txt Requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install -r Requirements.txt

RUN mkdir -p /home/app
RUN mkdir -p /home/app/data
RUN mkdir -p /home/app/data/rawData
RUN mkdir -p /home/app/data/analyzed
RUN mkdir -p /home/app/config
RUN mkdir -p /home/app/templates
WORKDIR /home/app/

COPY code /home/app
COPY ./code/templates /home/app/templates
EXPOSE 80
ENTRYPOINT ["python"]
CMD ["main.py"]