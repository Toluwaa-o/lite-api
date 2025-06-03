from fastapi import FastAPI
from cachetools import cached, TTLCache
from fastapi.responses import JSONResponse
from app.scrapper_functions.scrapper import information_scrapper
import uvicorn
import os

app = FastAPI()

cache = TTLCache(maxsize=100, ttl=3600*5)

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI-powered backend for Stears Lite, an economic data insights platform. Docs: /docs"}


@app.get("/information/{company}")
async def get_information(company: str):
    if company in cache:
        print("Returning cached data for", company)
        return JSONResponse(content=cache[company], status_code=200)
    
    try:
        data = information_scrapper(company)
        cache[company] = data
        print("Fetching fresh data for", company)
        return JSONResponse(content=data, status_code=200)
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[os.path.dirname(os.path.abspath(__file__))],
        reload_excludes=[
            "*/.git/*",
            "*/__pycache__/*",
            "*.pyc",
            "*/.pytest_cache/*",
            "*/.vscode/*",
            "*/.idea/*"
        ],
        reload_delay=1,
        reload_includes=["*.py", "*.html", "*.css", "*.js"]
    )