FROM python:3.10

# set the base installation, requirements are not changed often
RUN pip install --upgrade pip setuptools wheel

# install redis server
RUN apt update
RUN apt -y install redis

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# now add everything else, which changes often
COPY ./app ./app
COPY ./migrations ./migrations
COPY env.ini env.ini
COPY faq.json faq.json
COPY messages.json messages.json
COPY run.py run.py
COPY startup.sh startup.sh
RUN ["chmod", "+x", "./startup.sh"]

EXPOSE 8080

ENTRYPOINT [ "sh", "./startup.sh" ]
