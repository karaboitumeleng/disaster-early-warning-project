FROM python:3.12-slim
WORKDIR /app
# Build with: docker compose build --build-arg INSTALL_ML=1 api   (adds torch; image gets large)
ARG INSTALL_ML=0
COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_ML" = "1" ]; then pip install --no-cache-dir -r requirements-ml.txt; fi
COPY app ./app
RUN useradd -m appuser && chown -R appuser /app
USER appuser
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
