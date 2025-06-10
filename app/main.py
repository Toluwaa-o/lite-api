import os
import uvicorn
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from fastapi.encoders import jsonable_encoder
from pymongo import MongoClient
from fastapi import FastAPI, HTTPException
from cachetools import TTLCache
from fastapi.responses import JSONResponse
from app.scrapper_functions.scrapper import information_scrapper
# from app.scrapper_functions.functions.functions import get_macro_data, get_africamonitor_macro_data
# from app.scrapper_functions.data.data import country_codes, macro_indicator_dict

app = FastAPI()

origins = [
    "https://stears-lite.vercel.app",
    "http://localhost:3000/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
companies = db[os.getenv("MONGO_COLLECTION_ONE")]
countries = db[os.getenv("MONGO_COLLECTION_TWO")]

cache = TTLCache(maxsize=100, ttl=3600*5)


@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI-powered backend for Stears Lite, an economic data insights platform. Docs: /docs"}


@app.get("/information/{company}")
async def get_information(company: str):
    if not company.strip():
        return JSONResponse(content={"error": "Company name cannot be empty."}, status_code=400)

    if company.strip() in cache:
        print("Returning cached data for", company.strip())
        return JSONResponse(content=cache[company.strip()], status_code=200)

    try:
        # Check if company exists in the database
        existing = companies.find_one(
            {"company": {"$regex": f"^{company.strip()}$", "$options": "i"}})

        if existing:
            print("Returning data from database for", company.strip())

            existing.pop("_id", None)

            for key in ['created_at', 'updated_at']:
                if key in existing and isinstance(existing[key], datetime):
                    existing[key] = existing[key].isoformat()

            cache[company.strip()] = existing

            return JSONResponse(content=existing, status_code=200)

        print("Fetching fresh data for", company.strip())
        data = information_scrapper(company.strip())

        if "error" in data:
            raise HTTPException(status_code=400, detail=data["error"])

        company_dict = jsonable_encoder(data)
        now = datetime.now(timezone.utc).isoformat()
        company_dict["created_at"] = now
        company_dict["updated_at"] = now

        companies.insert_one(company_dict)
        company_dict.pop("_id", None)

        cache[company] = company_dict

        return JSONResponse(content=company_dict, status_code=200)

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
