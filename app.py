import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from generator.runner import run_generation

BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"
OUTPUT_DIR = BASE_DIR / "output"

app = FastAPI(title="Busbar App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


class GenerateRequest(BaseModel):
    bar_thickness: float = 10
    bar_width: float = 80
    bend_radius: float = 10
    drawing_lengths: list[float]
    bend_angles: list[float]
    length_reference: str = "outside"
    holes_by_segment: dict = Field(default_factory=dict)
    custom_circle_dim: float = 5.5
    custom_slot_width: float = 11
    custom_slot_length: float = 16
    custom_circle_dim2: float = 0
    filename: str = "busbar"


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/viewer")
async def viewer():
    return FileResponse(FRONTEND_DIR / "viewer.html")


@app.post("/generate")
async def generate(request: GenerateRequest):
    result = run_generation(request.model_dump())
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result)
    return result


@app.get("/output/{filename}")
async def download_output(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)


def open_browser():
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start()
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
