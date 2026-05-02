from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models.customer import Customer
from app.models.note import Note
from app.models.order import Order
from app.models.import_log import ImportLog
from app.models.action import Action

from app.routes.customers import router as customers_router
from app.routes.notes import router as notes_router
from app.routes.orders import router as orders_router
from app.routes.dashboard import router as dashboard_router
from app.routes.ai import router as ai_router
from app.routes.imports import router as imports_router
from app.routes.actions import router as actions_router
from app.routes.social_listener import router as social_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers_router)
app.include_router(notes_router)
app.include_router(orders_router)
app.include_router(dashboard_router)
app.include_router(ai_router)
app.include_router(imports_router)
app.include_router(actions_router)
app.include_router(social_router)
@app.get("/")
def root():
    return {"message": "Mini CRM AI backend is running"}