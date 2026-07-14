from __future__ import annotations

import enum
import importlib.util
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, List, cast


class Logger(object):
    @staticmethod
    def setup() -> logging.Logger:
        logger = logging.getLogger(__name__)

        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter(fmt="[ %(levelname)s ] %(message)s")
        )

        logger.addHandler(console_handler)

        return logger


class Dependencies(object):
    REQUIRED_LIBS: List[str] = ["questionary", "rich"]
    TEMP_DIR = "moon_moonrepo_setup_dependencies"

    class Status(enum.Enum):
        SATISFIED = enum.auto()
        MISSING = enum.auto()

    @staticmethod
    def is_available(library_name: str) -> bool:
        return importlib.util.find_spec(library_name) is not None

    @staticmethod
    def bootstrap(*, logger: logging.Logger) -> Dependencies.Status:
        missing_depencencies = [
            lib
            for lib in Dependencies.REQUIRED_LIBS
            if not Dependencies.is_available(lib)
        ]

        if not missing_depencencies:
            return Dependencies.Status.SATISFIED

        temp_dir = os.path.join(tempfile.gettempdir(), Dependencies.TEMP_DIR)
        os.makedirs(temp_dir, exist_ok=True)

        try:
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--target",
                    temp_dir,
                    "--quiet",
                    "--no-warn-script-location",
                ]
                + missing_depencencies,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            sys.path.insert(0, temp_dir)

            still_missing = [
                lib
                for lib in missing_depencencies
                if not Dependencies.is_available(lib)
            ]

            if not still_missing:
                logger.info("dependencies loaded succesfully")
                return Dependencies.Status.SATISFIED

            logger.error("failed to load some dependencies after install")
            return Dependencies.Status.MISSING
        except Exception as exception:
            logger.error(f"could not bootstrap dependencies: {exception}")

        return Dependencies.Status.MISSING


class Setup(object):
    def __init__(
        self, *, logger: logging.Logger, dependency_status: Dependencies.Status
    ) -> None:
        self.logger = logger
        self.dependency_status = dependency_status
        self.template_repository = "https://github.com/MauroGonzalez51/moon-monorepo"
        self.placeholders = dict(ORGANIZATION="@_ORG")
        self.ignore_directories = [".git", "node_modules", ".moon"]
        self.target_extensions = [".json", ".yml", ".yaml", ".md", ".ts", ".js"]

    def _separator(self, char: str = "-", width: int = 0) -> None:
        if width == 0:
            width = shutil.get_terminal_size(fallback=(80, 24)).columns
        sys.stdout.write(f"{char * width}\n")

    def _handle_remove_readonly(
        self, function: Callable[[str], None], path: str, exc_info: Any
    ) -> None:
        import stat

        os.chmod(path, stat.S_IWRITE)
        function(path)

    def _clean_git(self, directory: Path) -> None:
        target = directory / ".git"
        if target.exists() and target.is_dir():
            try:
                shutil.rmtree(target, onexc=self._handle_remove_readonly)
            except Exception:
                pass

    def _clone_repository(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)

            if (path / ".git").exists():
                self.logger.info(
                    "existing git repository detected in destination. skipping ..."
                )
                return True

            self.logger.info(f"cloning template repository into {path}")
            subprocess.run(
                ["git", "clone", self.template_repository, str(path)], check=True
            )

            self._clean_git(directory=path)

            return True
        except subprocess.CalledProcessError as exception:
            self.logger.error(f"failed to clone repository: {exception}")
            return False

    def _sanitize_scope(self, scope: str) -> str:
        return scope.replace("@", "").strip().lower().replace(" ", "-")

    def _apply_replacement(
        self, *, replacement_scope: str, repository_path: Path
    ) -> int:
        modified_files: int = 0
        replacement = f"@{replacement_scope}"

        for path in repository_path.rglob("*"):
            if not path.is_file():
                continue

            if any(ignored in path.parts for ignored in self.ignore_directories):
                continue

            if path.suffix in self.target_extensions:
                try:
                    content = path.read_text(encoding="utf-8")

                    if self.placeholders["ORGANIZATION"] in content:
                        path.write_text(
                            content.replace(
                                self.placeholders["ORGANIZATION"], replacement
                            ),
                            encoding="utf-8",
                        )
                        modified_files += 1
                except Exception as exception:
                    self.logger.info(f"could not update {path}: {exception}")

        return modified_files

    def _get_repository_path(self) -> Path:
        import questionary

        if self.dependency_status == Dependencies.Status.SATISFIED:
            return (
                Path(
                    questionary.path(
                        message="Repository Destination",
                        default=".",
                        only_directories=True,
                    ).ask()
                )
                .expanduser()
                .resolve()
            )

        return Path(input("Repository Destination").strip()).expanduser().resolve()

    def _get_scope(self) -> str:
        import questionary

        if self.dependency_status == Dependencies.Status.SATISFIED:
            import questionary
            from prompt_toolkit.document import Document
            from prompt_toolkit.validation import ValidationError, Validator

            class ScopeValidator(Validator):
                def validate(self, document: Document) -> None:
                    value = document.text.strip()

                    if not value:
                        raise ValidationError(message="cannot be empty")

                    if len(value.split(" ")) > 1:
                        raise ValidationError(message="cannot contain spaces")

            return cast(
                str,
                questionary.text(
                    message="Scope/Organization", validate=ScopeValidator()
                ).ask(),
            )

        return input("Scope/Organization").strip()

    def _get_confirmation(self, *, message: str) -> bool:
        import questionary

        if self.dependency_status == Dependencies.Status.SATISFIED:
            return cast(
                bool,
                questionary.confirm(
                    message=message,
                    default=False,
                ).ask(),
            )

        _input = input(f"{message} [y/N]")
        if _input == "y":
            return True

        return False

    def _header(self) -> None:
        if self.dependency_status == Dependencies.Status.SATISFIED:
            from rich import print as rprint
            from rich.panel import Panel

            rprint(
                Panel.fit(
                    "[bold magenta] Setup Wizard [/bold magenta]\n"
                    "[dim] configuring some parameters [/dim]\n",
                    border_style="cyan",
                )
            )

            return

        self._separator()
        sys.stdout.write("Setup Wizard - configuring some parameters\n")
        self._separator()

    def run(self) -> None:
        self._header()

        repository_path = self._get_repository_path()
        repository_path.mkdir(parents=True, exist_ok=True)

        if any(repository_path.iterdir()):
            should_continue = self._get_confirmation(
                message="Target directory is not empty, continue?"
            )

            if not should_continue:
                return

        scope_input = self._get_scope()
        if not scope_input:
            self.logger.info("scoped cannot be empty. exiting")
            return

        if len(scope_input.split(" ")) > 1:
            self.logger.error("scope cannot contain spaces")
            return

        if not self._clone_repository(path=repository_path):
            self.logger.info("repository not clonned. exiting...")
            return

        self._apply_replacement(
            replacement_scope=self._sanitize_scope(scope=scope_input),
            repository_path=repository_path,
        )


def main() -> None:
    logger = Logger.setup()

    status = Dependencies.bootstrap(logger=logger)
    Setup(logger=logger, dependency_status=status).run()


if __name__ == "__main__":
    main()
