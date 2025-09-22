FROM python:3.12-slim

WORKDIR /app

# 使用阿里云 Debian 镜像源，加速 apt-get
RUN rm -rf /etc/apt/sources.list* \
    && echo "deb https://mirrors.aliyun.com/debian/ trixie main contrib non-free" > /etc/apt/sources.list \
    && echo "deb https://mirrors.aliyun.com/debian/ trixie-updates main contrib non-free" >> /etc/apt/sources.list \
    && echo "deb https://mirrors.aliyun.com/debian-security/ trixie-security main contrib non-free" >> /etc/apt/sources.list \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get update \
    && apt-get install -y gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements (without mem0ai)
COPY server/requirements.txt .
RUN sed '/mem0ai/d' requirements.txt > requirements_no_mem0.txt && \
    pip install --no-cache-dir -r requirements_no_mem0.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy our modified mem0 source code and performance monitoring
COPY mem0 /app/mem0
COPY performance_monitoring /app/performance_monitoring

# Install dependencies for mem0 (including PostgreSQL support and Doubao SDK)
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    openai posthog protobuf pytz qdrant-client sqlalchemy psycopg2-binary volcengine-python-sdk

# Copy application code
COPY server .

# Create history directory
RUN mkdir -p /app/history

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
# Add both mem0 source and performance monitoring to Python path
ENV PYTHONPATH="/app:/app/performance_monitoring"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]