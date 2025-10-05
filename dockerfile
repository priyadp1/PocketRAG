FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY . .
ENV PYTHONUNBUFFERED=1 PORT=5050
EXPOSE 5050
CMD ["gunicorn","-w","2","-k","gthread","--threads","8","--timeout","180","-b","0.0.0.0:5050","app:app"]