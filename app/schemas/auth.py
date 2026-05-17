from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"username": "admin", "password": "changeme"}]
        }
    }


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
