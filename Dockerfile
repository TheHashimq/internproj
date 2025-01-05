FROM python:3.9-slim
RUN apt-get update && apt-get install -y traceroute iputils-ping
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000
ENV NAME World
CMD ["python", "app.py"]

