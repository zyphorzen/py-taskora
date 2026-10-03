from pydantic import BaseModel, ConfigDict, model_validator
from app.schemas.user import UserRegister, UserResponse


class UserLogin(BaseModel):
    username: str | None = None
    email: str | None = None
    password: str

    @model_validator(mode="after")
    def check_identifier(self) -> "UserLogin":
        if not self.username and not self.email:
            raise ValueError("Either email or username must be provided")
        return self


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(from_attributes=True)


class TokenPayload(BaseModel):
    sub: str | None = None
    exp: int | None = None


__all__ = ["UserLogin", "UserRegister", "UserResponse", "Token", "TokenPayload"]
