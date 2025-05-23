from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.database.db import get_db
from src.schemas.user import UserCreate, UserLogin, UserResponse, Token
from src.core.security import (
    get_current_user,
    get_password_hash,
    authenticate_user,
    create_access_token,
)
from src.models.user import User
from src.utils.exceptions import DatabaseError, InvalidInputError
import logging
from pydantic import BaseModel, ValidationError
from typing import Any, Optional

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


# Generic response model
class ApiResponse(BaseModel):
    status: str = "success"
    message: str
    data: Optional[Any] = None


router = APIRouter()


@router.post(
    "/register", response_model=ApiResponse, status_code=status.HTTP_201_CREATED
)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.email == user.email).first()
        if db_user:
            logger.warning(
                f"Registration attempt with already registered email: {user.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email, full_name=user.full_name, password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        logger.info(f"User registered successfully: {user.email}")
        return ApiResponse(
            message="User registered successfully",
            data=UserResponse(
                id=db_user.id, email=db_user.email, full_name=db_user.full_name
            ),
        )

    except ValidationError as e:
        logger.error(f"Validation error during registration: {str(e)}")
        raise InvalidInputError(detail=str(e))
    except SQLAlchemyError as e:
        logger.error(f"Database error during registration: {str(e)}")
        db.rollback()
        raise DatabaseError(detail="Failed to register user due to database error")
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
    
@router.post("/login", response_model=ApiResponse)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT token with user details.
    """
    try:
        db_user = authenticate_user(db, user.email, user.password)
        if not db_user:
            logger.warning(f"Failed login attempt for email: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Ensure db_user is valid
        if not hasattr(db_user, 'email'):
            logger.error("Authentication returned invalid user object")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )

        # Construct UserResponse explicitly
        user_response = UserResponse(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name
        )

        # Construct Token and ApiResponse
        access_token = create_access_token(data={"sub": db_user.email})
        logger.info(f"User logged in successfully: {user.email}")
        return ApiResponse(
            status="success",
            message="Login successful",
            data=Token(
                access_token=access_token,
                token_type="bearer",
                user=user_response
            )
        )

    except HTTPException as e:
        logger.warning(f"Authentication failure: {str(e)}")
        raise e  # Re-raise to preserve 401 status code
    except ValidationError as e:
        logger.error(f"Validation error during login: {str(e)}")
        return ApiResponse(
            status="error",
            message=f"Invalid input: {str(e)}",
            data=None
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during login: {str(e)}")
        raise DatabaseError(detail="Failed to login due to database error")
    except AttributeError as e:
        logger.error(f"bcrypt error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/me", response_model=ApiResponse)
async def get_current_user_info(user=Depends(get_current_user)):
    return ApiResponse(
        message="User details retrieved",
        data=UserResponse(id=user.id, email=user.email, full_name=user.full_name),
    )
