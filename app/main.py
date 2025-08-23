from fastapi.applications import FastAPI
from app.configs import create_app

app: FastAPI = create_app()
