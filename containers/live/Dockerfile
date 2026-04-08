FROM apache/airflow:3.1.8-python3.11

USER airflow

COPY --chown=airflow:root containers/live/requirements.txt /requirements.txt

RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

COPY --chown=airflow:root dags /opt/airflow/dags
COPY --chown=airflow:root web_scraping /opt/airflow/project/web_scraping

RUN umask 0002; mkdir -p /opt/airflow/project/web_scraping/runtime

ENV PYTHONPATH=/opt/airflow/project
