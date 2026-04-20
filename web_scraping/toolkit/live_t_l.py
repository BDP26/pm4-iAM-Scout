from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


class LiveTL:
    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.transform_compose_dir = self.project_root / "containers" / "transform"
        self.transform_compose_file = self.transform_compose_dir / "docker-compose.yml"

        self.database_compose_dir = self.project_root / "containers" / "database"
        self.database_compose_file = self.database_compose_dir / "docker-compose.yml"

    @staticmethod
    def _try_command(command: list[str]) -> subprocess.CompletedProcess[str] | None:
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
        docker_compose_cmd = ["docker", "compose"]
        docker_compose_legacy_cmd = ["docker-compose"]

        test_compose = self._try_command(docker_compose_cmd + ["version"])
        if test_compose is not None and test_compose.returncode == 0:
            return docker_compose_cmd

        test_legacy = self._try_command(docker_compose_legacy_cmd + ["version"])
        if test_legacy is not None and test_legacy.returncode == 0:
            return docker_compose_legacy_cmd

        docker_compose_stderr = (
            test_compose.stderr if test_compose is not None else "docker compose not found"
        )
        docker_compose_stdout = (
            test_compose.stdout if test_compose is not None else ""
        )
        legacy_stderr = (
            test_legacy.stderr if test_legacy is not None else "docker-compose not found"
        )
        legacy_stdout = (
            test_legacy.stdout if test_legacy is not None else ""
        )

        raise RuntimeError(
            "Neither 'docker compose' nor 'docker-compose' is available.\n\n"
            f"docker compose stdout:\n{docker_compose_stdout}\n"
            f"docker compose stderr:\n{docker_compose_stderr}\n\n"
            f"docker-compose stdout:\n{legacy_stdout}\n"
            f"docker-compose stderr:\n{legacy_stderr}"
        )

    def _run_compose_service(
        self,
        compose_dir: Path,
        compose_file: Path,
        service_name: str,
    ) -> subprocess.CompletedProcess[str]:
        if not compose_file.exists():
            raise FileNotFoundError(f"docker-compose.yml not found: {compose_file}")

        compose_cmd = self._detect_compose_command()

        command = [
            *compose_cmd,
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

    def run_transform_container(self) -> subprocess.CompletedProcess[str]:
        return self._run_compose_service(
            compose_dir=self.transform_compose_dir,
            compose_file=self.transform_compose_file,
            service_name="transform",
        )

    def run_update_data_container(self) -> subprocess.CompletedProcess[str]:
        return self._run_compose_service(
            compose_dir=self.database_compose_dir,
            compose_file=self.database_compose_file,
            service_name="update_data",
        )

    def delete_csv_files(self, directory: Path) -> None:
        if not directory.exists():
            print(f"Directory does not exist, skipping: {directory}")
            return

        for csv_file in directory.rglob("*.csv"):
            csv_file.unlink()
            print(f"Deleted: {csv_file}")


def main() -> None:
    service = LiveTL()

    print("Starting transform container...")
    transform_response = service.run_transform_container()
    print(transform_response.stdout)

    print("Starting update_data container...")
    update_response = service.run_update_data_container()
    print(update_response.stdout)

    scrape_dir = service.project_root / "data" / "scrape"
    transform_dir = service.project_root / "data" / "transform"

    #print("Deleting CSV files in scrape directory...")
    #service.delete_csv_files(scrape_dir)

    #print("Deleting CSV files in transform directory...")
    #service.delete_csv_files(transform_dir)


if __name__ == "__main__":
    main()