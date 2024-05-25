from pydantic import BaseModel
from pydantic.fields import Field

class UserDetails(BaseModel):
    # use this to add more schemas
    userid: str = Field(..., example="userid")
    password: str = Field(..., example="password")