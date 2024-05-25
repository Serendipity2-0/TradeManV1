from fastapi import FastAPI
import uvicorn
from fastapi.openapi.docs import get_swagger_ui_html
from applications.user import main as user
from fastapi import APIRouter


app = FastAPI()
app_v1 = APIRouter()


@app.get("/swagger", include_in_schema=False)
def overridden_swagger():
    return get_swagger_ui_html(openapi_url="openapi.json", title="Trademan")

app_v1.include_router(user.user_router , prefix="/user" , tags=["user"])
app.include_router(app_v1, prefix='/v1')



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
