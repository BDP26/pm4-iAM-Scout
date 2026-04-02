FROM apache/airflow:3.1.8-python3.11

USER airflow

COPY containers/live/requirements.txt /requirements.txt

RUN pip install --no-cache-dir "apache-airflow==3.1.8" -r /requirements.txt

COPY dags /opt/airflow/dags
COPY web_scraping /opt/airflow/project/web_scraping

ENV PYTHONPATH=/opt/airflow/project
