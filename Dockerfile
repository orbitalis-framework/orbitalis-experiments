FROM python:3.12-slim

WORKDIR /workspace

COPY requirements.txt /workspace/

RUN pip install --upgrade pip && \
    pip install -r /workspace/requirements.txt

ENTRYPOINT ["python", "main.py"]