# Backend entry point: loads the environment and starts the FastAPI app with Uvicorn.
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )
