from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db, User, AdminUser
from app.models.auth import UserLoginRequest, AuthResponse, UserResponse
from app.core.auth import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/login", response_model=AuthResponse)
async def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return access token"""
    
    print(f"🔍 LOGIN DEBUG: Attempting login for email: {request.email}")
    
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    print(f"🔍 LOGIN DEBUG: User found: {user is not None}")
    if user:
        print(f"🔍 LOGIN DEBUG: User email: {user.email}, active: {user.is_active}")
    
    if not user or not verify_password(request.password, user.password_hash):
        print(f"🔍 LOGIN DEBUG: Authentication failed - user exists: {user is not None}")
        if user:
            print(f"🔍 LOGIN DEBUG: Password verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    print(f"🔍 LOGIN DEBUG: Creating response for user: {user.email}")
    
    response = {
        "access_token": access_token,
        "user": UserResponse.model_validate(user).model_dump()
    }
    
    print(f"🔍 LOGIN DEBUG: Response created successfully, returning to client")
    return response

@router.post("/admin/login", response_model=AuthResponse)
async def admin_login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate admin user and return access token"""
    
    print(f"🔍 ADMIN LOGIN DEBUG: Attempting admin login for email: {request.email}")
    
    # Find admin user
    admin_user = db.query(AdminUser).filter(AdminUser.email == request.email).first()
    print(f"🔍 ADMIN LOGIN DEBUG: Admin user found: {admin_user is not None}")
    
    if not admin_user or not verify_password(request.password, admin_user.password_hash):
        print(f"🔍 ADMIN LOGIN DEBUG: Admin authentication failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not admin_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token with admin flag
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": admin_user.email, "admin": True}, expires_delta=access_token_expires
    )
    
    print(f"🔍 ADMIN LOGIN DEBUG: Creating admin response for: {admin_user.email}")
    
    # Create user response from admin user
    user_response = {
        "id": admin_user.id,
        "email": admin_user.email,
        "name": admin_user.name,
        "company": "Admin",
        "beta_code": "",
        "is_active": admin_user.is_active,
        "created_at": admin_user.created_at
    }
    
    response = {
        "access_token": access_token,
        "user": user_response
    }
    
    print(f"🔍 ADMIN LOGIN DEBUG: Admin response created successfully")
    return response