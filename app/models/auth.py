from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Request Models
class UserSignupRequest(BaseModel):
    beta_code: str
    name: str
    email: EmailStr
    password: str
    company: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str

class GenerateBetaCodeRequest(BaseModel):
    quantity: int = 1

# Response Models
class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    company: Optional[str]
    beta_code: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AdminResponse(BaseModel):
    id: int
    email: str
    name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class BetaCodeResponse(BaseModel):
    id: int
    code: str
    is_used: bool
    used_by_user_id: Optional[int]
    created_at: datetime
    used_at: Optional[datetime]

    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class AdminAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminResponse

class GenerateBetaCodeResponse(BaseModel):
    codes: list[str]
    message: str

class TokenData(BaseModel):
    email: Optional[str] = None
