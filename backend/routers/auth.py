from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.models.user import UserRegister, UserLogin, UserResponse, TokenResponse
from backend.services.auth_service import register_user, authenticate_user, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required."
        )
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )
    return UserResponse(
        id=payload.get("sub"),
        username=payload.get("username", "User"),
        email=payload.get("email", "")
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister):
    """Register a new user account."""
    user, err = register_user(data.username, data.email, data.password)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    token = create_access_token({
        "sub": user["id"],
        "username": user["username"],
        "email": user["email"]
    })

    return TokenResponse(
        access_token=token,
        user=UserResponse(**user)
    )


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin):
    """Authenticate with email and password."""
    user, err = authenticate_user(data.email, data.password)
    if err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err)

    token = create_access_token({
        "sub": user["id"],
        "username": user["username"],
        "email": user["email"]
    })

    return TokenResponse(
        access_token=token,
        user=UserResponse(**user)
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get currently logged-in user profile."""
    return current_user
