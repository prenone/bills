FROM python:slim-bullseye

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD /app/run_prod.sh