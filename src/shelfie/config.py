from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    google_books_api_key: str = ""
    myreads_data_dir: Path = Path.home() / ".myreads"
    openai_model: str = "gpt-5.2"
    openai_embedding_model: str = "text-embedding-3-small"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def tinydb_path(self) -> Path:
        return self.myreads_data_dir / "reads.json"

    @property
    def chroma_path(self) -> Path:
        return self.myreads_data_dir / "chroma"

    def ensure_data_dir(self) -> None:
        self.myreads_data_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()
