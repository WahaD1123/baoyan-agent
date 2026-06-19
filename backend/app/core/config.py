import os
from pathlib import Path
from functools import lru_cache


_loaded_env_files: list[str] = []


class Settings:
    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        root_env = project_root / ".env"
        backend_env = project_root / "backend" / ".env"
        _load_env_file(root_env)
        _load_env_file(backend_env)
        self.app_name = os.getenv("APP_NAME", "Baoyan Agent")
        self.app_env = os.getenv("APP_ENV", "development")
        self.backend_cors_origins = os.getenv(
            "BACKEND_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
        self.llm_provider = os.getenv("LLM_PROVIDER", "mock")
        self.llm_api_key = os.getenv("LLM_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "")
        self.llm_model = os.getenv("LLM_MODEL", "qwen-vl-max")
        self.llm_critic_model = os.getenv("LLM_CRITIC_MODEL", "qwen3.6-flash")
        self.llm_critic_max_tokens = _env_int("LLM_CRITIC_MAX_TOKENS", 400)
        self.llm_member_c_fallback_model = os.getenv("LLM_MEMBER_C_FALLBACK_MODEL", "qwen3.6-flash")
        self.llm_member_c_max_tokens = _env_int("LLM_MEMBER_C_MAX_TOKENS", 1200)
        self.loaded_env_files = list(dict.fromkeys(_loaded_env_files))
        self.expected_env_files = [str(root_env), str(backend_env)]

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    _loaded_env_files.append(str(path))
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default
