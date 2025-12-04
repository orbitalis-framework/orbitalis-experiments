FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y tk tk-dev

WORKDIR /workspace

COPY requirements.txt /workspace/

RUN pip install --upgrade pip && pip install -r /workspace/requirements.txt

ENTRYPOINT ["python", "-O", "main.py"]