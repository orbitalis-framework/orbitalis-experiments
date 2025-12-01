FROM python:3.12-slim

WORKDIR /workspace

COPY requirements.txt /workspace/

RUN apt-get update && \
    apt-get install -y tk tk-dev && \
    pip install --upgrade pip && \
    pip install -r /workspace/requirements.txt

ENTRYPOINT ["python", "main.py"]