"""
Live Transform and Load Pipeline

This module orchestrates the live data transformation and database load processes.
It coordinates Docker containers to:
- Transform newly scraped data
- Apply machine learning rating model
- Apply recommender model predictions
- Load results into the database

Main class:
- LiveTL: Orchestrates the complete live pipeline execution
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

LIVE_IMAGE_NAME = "iamscout-live"
DEFAULT_DB_URL = "postgresql+psycopg2://postgres:postgres@host.docker.internal:5434/iamscout"
RATING_MODEL_MODULE = "ml.rating_model.apply_model"
RECOMMENDER_MODEL_MODULE = "ml.recommender_model.apply_model"
TRANSFORM_SERVICE_NAME = "transform"
UPDATE_DATA_SERVICE_NAME = "update_data"
PROJECT_ROOT_CONTAINER_PATH = "/workspace"
PYTHONPATH_CONTAINER_VALUE = "/workspace"


class LiveTL:
    """Run live transform, ML rating, ML prediction, and database load steps."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        db_url: str = DEFAULT_DB_URL,
    ) -> None:
        """Initialize paths and runtime settings for the live pipeline."""
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.db_url = db_url
        self.transform_compose_dir = self.project_root / "containers" / "transform"
        self.transform_compose_file = self.transform_compose_dir / "docker-compose.yml"
        self.database_compose_dir = self.project_root / "containers" / "database"
        self.database_compose_file = self.database_compose_dir / "docker-compose.yml"

    @staticmethod
    def _try_command(command: list[str]) -> subprocess.CompletedProcess[str] | None:
        """Run a command and return None when the executable is missing."""
        try:
            return subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return None

    def _detect_compose_command(self) -> list[str]:
        """Detect whether Docker Compose is available as plugin or legacy binary."""
        docker_compose_command = ["docker", "compose"]
        docker_compose_legacy_command = ["docker-compose"]

        compose_result = self._try_command(docker_compose_command + ["version"])
        if compose_result is not None and compose_result.returncode == 0:
            return docker_compose_command

        legacy_result = self._try_command(docker_compose_legacy_command + ["version"])
        if legacy_result is not None and legacy_result.returncode == 0:
            return docker_compose_legacy_command

        compose_stdout = compose_result.stdout if compose_result is not None else ""
        compose_stderr = (
            compose_result.stderr if compose_result is not None else "docker compose not found"
        )
        legacy_stdout = legacy_result.stdout if legacy_result is not None else ""
        legacy_stderr = (
            legacy_result.stderr if legacy_result is not None else "docker-compose not found"
        )

        raise RuntimeError(
            "Neither 'docker compose' nor 'docker-compose' is available.\n\n"
            f"docker compose stdout:\n{compose_stdout}\n"
            f"docker compose stderr:\n{compose_stderr}\n\n"
            f"docker-compose stdout:\n{legacy_stdout}\n"
            f"docker-compose stderr:\n{legacy_stderr}"
        )

    def _run_compose_service(
        self,
        compose_dir: Path,
        compose_file: Path,
        service_name: str,
    ) -> subprocess.CompletedProcess[str]:
        """Run a Docker Compose service and fail when the service exits with an error."""
        if not compose_file.exists():
            raise FileNotFoundError(f"docker-compose.yml not found: {compose_file}")

        compose_command = self._detect_compose_command()
        command = [
            *compose_command,
            "-f",
            str(compose_file),
            "up",
            "--build",
            "--abort-on-container-exit",
            "--exit-code-from",
            service_name,
            service_name,
        ]

        result = subprocess.run(
            command,
            cwd=compose_dir,
            check=False,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Error while starting the {service_name} container.\n"
                f"Command:\n{' '.join(command)}\n\n"
                f"STDOUT:\n{result.stdout}\n\n"
                f"STDERR:\n{result.stderr}"
            )

        return result

    def _run_live_python_module(
        self,
        module_name: str,
        step_name: str,
    ) -> subprocess.CompletedProcess[str]:
        """Run a project Python module inside the live Docker image."""
        command = [
            "docker",
            "run",
            "--rm",
            "-e",
            f"PYTHONPATH={PYTHONPATH_CONTAINER_VALUE}",
            "-e",
            f"IAMSCOUT_DB_URL={self.db_url}",
            "-v",
            f"{self.project_root}:{PROJECT_ROOT_CONTAINER_PATH}",
            "-w",
            PROJECT_ROOT_CONTAINER_PATH,
            LIVE_IMAGE_NAME,
            "python",
            "-m",
            module_name,
            "--project-root",
            PROJECT_ROOT_CONTAINER_PATH,
            "--db-url",
            self.db_url,
        ]

        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Error while running {step_name}.\n"
                f"Command:\n{' '.join(command)}\n\n"
                f"STDOUT:\n{result.stdout}\n\n"
                f"STDERR:\n{result.stderr}"
            )

        return result

    def run_transform_container(self) -> subprocess.CompletedProcess[str]:
        """Run the transform container."""
        return self._run_compose_service(
            compose_dir=self.transform_compose_dir,
            compose_file=self.transform_compose_file,
            service_name=TRANSFORM_SERVICE_NAME,
        )

    def run_rating_model_prediction(self) -> subprocess.CompletedProcess[str]:
        """Run the rating model prediction inside the live Docker image."""
        return self._run_live_python_module(
            module_name=RATING_MODEL_MODULE,
            step_name="rating model prediction",
        )

    def run_recommender_model_prediction(self) -> subprocess.CompletedProcess[str]:
        """Run the recommender model prediction inside the live Docker image."""
        return self._run_live_python_module(
            module_name=RECOMMENDER_MODEL_MODULE,
            step_name="recommender model prediction",
        )

    def run_update_data_container(self) -> subprocess.CompletedProcess[str]:
        """Run the database update container."""
        return self._run_compose_service(
            compose_dir=self.database_compose_dir,
            compose_file=self.database_compose_file,
            service_name=UPDATE_DATA_SERVICE_NAME,
        )

    def delete_csv_files(self, directory: Path) -> None:
        """Delete CSV files in a directory tree."""
        if not directory.exists():
            print(f"[INFO] Directory does not exist, skipping: {directory}")
            return

        for csv_file in directory.rglob("*.csv"):
            csv_file.unlink()
            print(f"[INFO] Deleted: {csv_file}")


def main() -> None:
    """Run transform, rating prediction, recommender prediction, and database load."""
    service = LiveTL()

    print("[INFO] Starting transform container")
    transform_response = service.run_transform_container()
    print(transform_response.stdout)

    print("[INFO] Applying rating model to transformed player_stats.csv")
    rating_response = service.run_rating_model_prediction()
    print(rating_response.stdout)

    print("[INFO] Applying recommender model to current-season player data")
    recommender_response = service.run_recommender_model_prediction()
    print(recommender_response.stdout)

    print("[INFO] Starting update_data container")
    update_response = service.run_update_data_container()
    print(update_response.stdout)


if __name__ == "__main__":
    main()
