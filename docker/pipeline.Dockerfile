FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Tesseract: a second reading of pages where the scan's own text layer is too noisy
# (entry numbers, the index).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-fra tesseract-ocr-deu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work/pipeline
COPY pipeline/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ENV PYTHONPATH=/work/pipeline
CMD ["python", "-m", "denombrement"]
