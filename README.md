# iAM-Scout

iAM-Scout is a data-driven scouting prototype for Swiss amateur football.  
The project collects publicly available football data, processes and stores it in a structured database, applies machine learning models, and provides scouting insights through an API and a Streamlit frontend.

## Project Overview

The system is built as an end-to-end data pipeline:

1. **Web scraping** of publicly available football data
2. **Data transformation / ETL** for cleaning and standardisation
3. **PostgreSQL database** for structured storage
4. **Machine learning models** for player ratings and recommendations
5. **FastAPI backend** for data access
6. **Streamlit frontend** for visualising scouting insights
7. **Airflow DAGs** for scheduled data updates

Most components are executed through Docker containers.  
This ensures that the system can be started in a reproducible way without setting up a local Python virtual environment.

## Repository Structure

```text
.
├── backend/
├── containers/
│   ├── database/
│   │   └── sql/
│   ├── live/
│   │   └── dags/
│   ├── scraping/
│   ├── transform/
│   └── update_data/
│       └── sql/
├── dags/
├── data/
│   ├── scrape/
│   └── transform/
├── documentation/
├── ml/
│   ├── rating_model/
│   ├── recommender_model/
│   └── toolkit/
└── web_scraping/
    ├── live/
    ├── runtime/
    ├── scripts/
    ├── transfermarkt/
    ├── sofascore/
    └── toolkit/
```

## Requirements

The following tools are required:

- Docker
- Git
- Optional: PostgreSQL client for manual database inspection


## Setup

### 1. Clone the repository

```bash
<COMMAND_CLONE_REPOSITORY>
```

### 2. Change into the project directory

```bash
<COMMAND_CHANGE_TO_PROJECT_DIRECTORY>
```

### 3. Build the containers

```bash
<COMMAND_BUILD_CONTAINERS>
```


## Running the Application

The application is executed mainly through Docker containers.  
The recommended execution order is:

1. Run the scraping container and scraping scripts
2. Run the transformation container
3. Run the rating model pipeline
4. Run the recommender model pipeline
5. Run the database container
6. Run backend and frontend
7. Start the Airflow live DAGs

### 1. Run the scraping container

The scraping container is located in:

```text
containers/scraping/
```

Start or run the scraping container:

```bash
<COMMAND_RUN_SCRAPING_CONTAINER>
```

After the scraping container is running, execute the scraping scripts in the following order:

```bash
<COMMAND_RUN_MAIN_TM_AM>
<COMMAND_RUN_MAIN_TM_PRO>
<COMMAND_RUN_MAIN_SS>
```

The scripts are located in:

```text
web_scraping/scripts/
```

### 2. Run the transformation container

The transformation logic is located in:

```text
containers/transform/
```

Run the transformation container:

```bash
<COMMAND_RUN_TRANSFORM_CONTAINER>
```

### 3. Run the rating model pipeline

The rating model is located in:

```text
ml/rating_model/
```

Run the files in the following order:

1. `merge.ipynb`
2. `model.ipynb`
3. `apply_model.py`

```bash
<COMMAND_RUN_RATING_MERGE_NOTEBOOK>
<COMMAND_RUN_RATING_MODEL_NOTEBOOK>
<COMMAND_RUN_RATING_APPLY_MODEL>
```

### 4. Run the recommender model pipeline

The recommender model is located in:

```text
ml/recommender_model/
```

Run the files in the following order:

1. `feature_engineering.ipynb`
2. `model.ipynb`
3. `league_difference.ipynb`
4. `apply_model.py`

```bash
<COMMAND_RUN_RECOMMENDER_FEATURE_ENGINEERING_NOTEBOOK>
<COMMAND_RUN_RECOMMENDER_MODEL_NOTEBOOK>
<COMMAND_RUN_RECOMMENDER_LEAGUE_DIFFERENCE_NOTEBOOK>
<COMMAND_RUN_RECOMMENDER_APPLY_MODEL>
```

### 5. Start the database container

The PostgreSQL database setup is located in:

```text
containers/database/
```

Start the database container:

```bash
<COMMAND_START_DATABASE_CONTAINER>
```


### 6. Start the backend

The FastAPI backend is located in:

```text
backend/
```

Start the backend container:

```bash
<COMMAND_START_BACKEND_CONTAINER>
```

After startup, the API should be available at:

```text
http://<HOST>:<PORT>
```

### 7. Start the frontend

The frontend is implemented with Streamlit.

Start the frontend container:

```bash
<COMMAND_START_FRONTEND_CONTAINER>
```

After startup, the frontend should be available in the browser at:

```text
http://<HOST>:<PORT>
```

### 8. Start Airflow live DAGs

Apache Airflow is used to schedule recurring live updates.

The DAGs are located in:

```text
dags/
containers/live/dags/
```

Start the Airflow live container:

```bash
<COMMAND_START_AIRFLOW_LIVE_CONTAINER>
```

Trigger the live DAGs:

```bash
<COMMAND_TRIGGER_AIRFLOW_LIVE_DAGS>
```

## Known Limitations

- The `player_stats` scraper is currently not working because Transfermarkt changed parts of its website structure.

## Team

- Fabian Meier
- Cedric Niklaus

## Project Status

Prototype developed as part of the **Big Data Project PM4** module.

## Links

- GitHub Repository: https://github.com/BDP26/pm4-iAM-Scout
- Trello Board: https://trello.com/b/2lD8WGPz/iam-scout
