FROM python:3.12-slim

WORKDIR /app

# OpenCV (pulled in by ultralytics) needs these shared libraries.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Bake the weights into the image so the container runs offline.
RUN python -c "from app.classifier import resolve_weights; print(resolve_weights())"

# Ultralytics must not try to pip-install packages at runtime.
ENV YOLO_AUTOINSTALL=false

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
