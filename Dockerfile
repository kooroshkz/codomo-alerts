FROM python:3.14-slim

LABEL org.opencontainers.image.title="codomo-alerts" \
      org.opencontainers.image.description="Self-hosted alerts for new Codomo homes (formerly Holland2Stay) in the Netherlands, Spain, Portugal and Austria" \
      org.opencontainers.image.source="https://github.com/kooroshkz/codomo-alerts" \
      org.opencontainers.image.url="https://kooroshkz.github.io/codomo-alerts/" \
      org.opencontainers.image.documentation="https://github.com/kooroshkz/codomo-alerts#readme" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CODOMO_DATA_DIR=/data \
    CODOMO_HOST=0.0.0.0 \
    TZ=Europe/Amsterdam

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install . && rm -rf /src

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data /config \
    && chown app:app /data /config

USER app
# a config file mounted at /config/config.toml is picked up as ./config.toml
WORKDIR /config
VOLUME /data
EXPOSE 8080

HEALTHCHECK --interval=1m --timeout=5s --start-period=30s CMD ["codomo-alerts", "health"]

ENTRYPOINT ["codomo-alerts"]
CMD ["watch"]
