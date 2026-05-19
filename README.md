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


## Setup: Accessing the Application

The backend runs on the virtual machine.  
The frontend can be started locally and connects to the running backend.

### 1. Start the backend on the VM

Connect to the VM and start the backend:

```bash
sudo -E /home/ubuntu/pm4-iAM-Scout/.venv/bin/python main.py
```

### 2. Start the frontend locally

Create a local Python environment for the frontend:

```bash
python -m venv .venv
```

Activate the environment.

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the required frontend packages:

```bash
pip install streamlit requests pandas
```

Start the Streamlit frontend:

```bash
streamlit run frontend/Home.py
```

After startup, Streamlit will show the local URL in the terminal.  
Open this URL in the browser to access the iAM-Scout application.

```text
http://localhost:<PORT>
```


## Known Limitations

- The `player_stats` scraper is currently not working because Transfermarkt changed parts of its website structure.
- Transfermarkt blocked requests from the ZHAW network. As a result, scraping was also blocked from the ZHAW virtual machine.

## Team

- Fabian Meier
- Cedric Niklaus

## Project Status

Prototype developed as part of the **Big Data Project PM4** module.

## Links

- GitHub Repository: https://github.com/BDP26/pm4-iAM-Scout
- Trello Board: https://trello.com/b/2lD8WGPz/iam-scout
