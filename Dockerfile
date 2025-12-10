# 使用官方 Python 运行时作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（例如 libpq-dev 如果使用 PostgreSQL）
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建媒体和静态文件目录
RUN mkdir -p /app/media /app/static

# 收集静态文件（如果需要）
RUN python manage.py collectstatic --noinput || true

# 数据库迁移
RUN python manage.py migrate --noinput || true

# 暴露端口
EXPOSE 8000

# 启动应用（使用 Gunicorn）
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "DjangoPaddleOCR.wsgi:application"]
