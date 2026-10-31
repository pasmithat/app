from fastapi import FastAPI, APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import power_routes  # noqa: E402

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="UrbanShield AI")
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "UrbanShield AI API"}


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(x) for x in e["loc"] if x not in ("body", "query")) or "body",
               "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content=jsonable_encoder(
        {"detail": "; ".join(f"{e['field']}: {e['message']}" for e in errors), "errors": errors}))


power_routes.init(db)
app.include_router(api_router)
app.include_router(power_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
