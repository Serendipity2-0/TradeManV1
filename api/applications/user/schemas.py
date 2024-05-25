from pydantic import BaseModel
from pydantic.fields import Field

class LoginCredentials(BaseModel):
    userid: str = Field(..., example="userid")
    password: str = Field(..., example="password")