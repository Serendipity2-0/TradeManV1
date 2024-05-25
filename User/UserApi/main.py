from fastapi import FastAPI
import uvicorn
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi import APIRouter
from . import schemas
from . import app


app_fastapi = FastAPI()
app_user = APIRouter()

app_fastapi.include_router(app_user, prefix='/v1/user')




@app_fastapi.get("/swagger", include_in_schema=False)
def overridden_swagger():
    return get_swagger_ui_html(openapi_url="openapi.json", title="Trademan")


@app_user.post("/register")
def register_user(user_detail:schemas.UserDetails):
    return app.register_user(user_detail)




if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
