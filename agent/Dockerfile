FROM python:3.12-slim
WORKDIR /app

# 의존성·패키지 설치 (PyPI). src layout이라 pyproject + src 둘 다 필요.
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 9000
CMD ["uvicorn", "operagent.webhook:app", "--host", "0.0.0.0", "--port", "9000"]
