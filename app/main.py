from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(title="SAP EWA Expiration Analyzer")
app.include_router(router)
