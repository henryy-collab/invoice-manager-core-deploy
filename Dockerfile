FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip ca-certificates \
    && curl -sSL https://rclone.org/install.sh | bash \
    && apt-get purge -y unzip \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY local/ ./local/
COPY ui/ ./ui/

RUN pip install --no-cache-dir .

RUN mkdir -p /app/keys /root/.config/rclone /app/local/data

ENV PYTHONPATH=/app/local:/app/ui \
    RCLONE_CONFIG=/root/.config/rclone/rclone.conf

EXPOSE 8000

COPY deploy/entrypoint.sh /entrypoint.sh
COPY deploy/bootstrap.py /bootstrap.py
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "ui/web_ui.py"]
