from fastapi import FastAPI
from cachetools import cached, TTLCache
from fastapi.responses import JSONResponse
from app.scrapper_functions.scrapper import information_scrapper


app = FastAPI()

cache = TTLCache(maxsize=100, ttl=3600*5)

@app.get("/")
async def root():
    return {"message": "Hello, World!"}


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