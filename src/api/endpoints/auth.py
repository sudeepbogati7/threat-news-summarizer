from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.database.db import get_db
from src.schemas.user import UserCreate, UserResponse, Token
from src.core.security import get_password_hash, authenticate_user, create_access_token
from src.models.user import User
from src.utils.exceptions import DatabaseError, InvalidInputError
import logging
from pydantic import ValidationError

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with full name, email, and password.
    Returns a JSON response with user details.
    """
    try:
        # Check if email already exists
        db_user = db.query(User).filter(User.email == user.email).first()
        print("db user from register controller : ", db_user)
        if db_user:
            logger.warning(f"Registration attempt with already registered email: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password and create user
        hashed_password = get_password_hash(user.password)
        
        db_user = User(
            email=user.email,
            full_name=user.full_name,
            password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User registered successfully: {user.email}")
        return {
            "status": "success",
            "message": "User registered successfully",
            "data": {
                "id": db_user.id,
                "email": db_user.email,
                "full_name": db_user.full_name
            }
        }

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
            detail="An unexpected error occurred"
        )

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate user and return a JWT token.
    Returns a JSON response with token details and user info.
    """
    try:
        # Authenticate user
        user = authenticate_user(db, form_data.email, form_data.password)
        if not user:
            logger.warning(f"Failed login attempt for email: {form_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate JWT token
        access_token = create_access_token(data={"sub": user.email})
        logger.info(f"User logged in successfully: {user.email}")
        return {
            "status": "success",
            "message": "Login successful",
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name
                }
            }
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error during login: {str(e)}")
        raise DatabaseError(detail="Failed to login due to database error")
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )