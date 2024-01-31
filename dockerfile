FROM python:3.10

# set the base installation, requirements are not changed often
RUN pip install --upgrade pip setuptools wheel

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# now add everything else, which changes often
COPY . . 

EXPOSE 8080

CMD [ "python", "run.py" ]