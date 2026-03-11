# main.py
from fastapi import FastAPI
from app.api import router

app = FastAPI()
app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {"message": "PostReading Agent API"}