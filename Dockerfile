# 使用官方 Python 镜像作为基础镜像
FROM python:3.9-slim-buster

# 将工作目录设置为 /app
WORKDIR /app

# 复制当前目录下的所有文件到容器中的 /app 目录
COPY . .

# 安装项目所需的依赖
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080
ENV APP_ENV production

# 在容器启动时运行 web 应用
# CMD ["gunicorn", "-w", "4", "--bind", "0.0.0.0:8080", "app:app"]
CMD ["python", "app.py"]
