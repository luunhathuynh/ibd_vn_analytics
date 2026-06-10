"""Run API: uvicorn src.api.app:app --host 127.0.0.1 --port 8000"""

from __future__ import annotations

import uvicorn

from src.config import load_config


def main() -> None:
    cfg = load_config()
    api_cfg = cfg.get("api", {})
    host = api_cfg.get("host", "127.0.0.1")
    port = int(api_cfg.get("port", 8000))
    uvicorn.run("src.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
