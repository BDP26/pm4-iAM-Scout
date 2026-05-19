FROM postgres:16

WORKDIR /opt/update_data

COPY containers/database/sql /opt/db/sql
COPY containers/update_data/sql /opt/update_data/sql
COPY containers/update_data/run_update.sh /opt/update_data/run_update.sh

RUN chmod +x /opt/update_data/run_update.sh

ENTRYPOINT ["/opt/update_data/run_update.sh"]
