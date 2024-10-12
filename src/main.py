### REQIREMENTS ###

## Authentication
# 1. User needs to be able to create an account.
# 2. User needs to be able to log in.
# 3. Secure endponits with JWT.

## Authentication Endpoints
# 1. Register (POST) new user 
# /register
    # Response will be user object with JWT token.
# 2. Login an existing user. 
# /login
    # Response will be user object with JWT token.

## Image Management
#1. User must be able to upload images.
#2. Users must be able to perform  various operations on images.
    # Resize
    # Crop
    # Rotate
    # Watermark
    # Flip
    # Mirror
    # Compress
    # Change format (JPEG, PNG, etc.)
    # Apply filters (grayscale, sepia, etc.)
#3. Retrieve a saved image in different format.
    ##a. PNG
    ##b. JPEG
    ##c. WEBP
#4. List all uploaded images by a user with metadata.

## Image Management Endpoints
#1. Upload an image. (POST)
    # /images
    # Response: Upload image details, (URL, metadata)
#2. Apply Transformation to an image (POST)
    # /images/<image_id>/transform
    # Response: transformed image details (URL, metadata)
#3. Retrieve an image (GET)
    # /images/<image_id>
    # Response: Image details (URL, metadata)
#4. Get a paginated list of all images uploaded by a user. (GET)
    # /images?page=1&limit=10

### CHECK LIST ###
#1. Rate limiting to prevent abuse
#2. Caching images to improve performance
#3. Error handling and validation
#4. Message queue to process image transformations asynchronously

import os
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import boto3
from botocore.exceptions import NoCredentialsError
from mangum import Mangum
from dotenv import load_dotenv
from pydantic import BaseModel
from PIL import Image, ImageOps, ImageFilter
import io

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Initialize the S3 client
s3 = boto3.client('s3')
BUCKET_NAME = os.getenv('BUCKET_NAME')

# Initialize the Cognito client
cognito_client = boto3.client('cognito-idp')
USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')
CLIENT_ID = os.getenv('COGNITO_APP_CLIENT_ID')

# Ensure the environment variables are loaded correctly
if not USER_POOL_ID or not CLIENT_ID:
    raise ValueError("Missing Cognito configuration. Please check your environment variables.")

# JWT settings
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserRegister(BaseModel):
    username: str
    password: str
    email: str

@app.post("/register")
async def register(user: UserRegister):
    try:
        response = cognito_client.sign_up(
            ClientId=CLIENT_ID,
            Username=user.username,
            Password=user.password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': user.email
                }
            ]
        )
        return {"message": "User registered successfully"}
    except cognito_client.exceptions.UsernameExistsException:
        raise HTTPException(status_code=400, detail="Username already registered")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/token", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': form_data.username,
                'PASSWORD': form_data.password
            }
        )
        return {
            "access_token": response['AuthenticationResult']['AccessToken'],
            "token_type": "bearer"
        }
    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/me")
async def read_users_me(token: str = Depends(oauth2_scheme)):
    try:
        response = cognito_client.get_user(
            AccessToken=token
        )
        return response['UserAttributes']
    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list-s3-objects/")
async def list_s3_objects(token: str = Depends(oauth2_scheme)):
    try:
        response = cognito_client.get_user(
            AccessToken=token
        )
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        if 'Contents' in response:
            return [{"filename": obj["Key"], "size": obj["Size"]} for obj in response['Contents']]
        else:
            return []
    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid token")
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="Credentials not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/images")
async def upload_image(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    try:
        response = cognito_client.get_user(
            AccessToken=token
        )
        contents = await file.read()
        s3.put_object(Bucket=BUCKET_NAME, Key=file.filename, Body=contents)
        return {"filename": file.filename, "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{file.filename}"}
    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid token")
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="Credentials not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/images/{image_id}/transform")
async def transform_image(image_id: str, operation: str, token: str = Depends(oauth2_scheme)):
    try:
        response = cognito_client.get_user(
            AccessToken=token
        )
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=image_id)
        image = Image.open(io.BytesIO(obj['Body'].read()))

        if operation == "resize":
            image = image.resize((100, 100))
        elif operation == "rotate":
            image = image.rotate(90)
        elif operation == "grayscale":
            image = ImageOps.grayscale(image)
        # Add more operations as needed

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)

        s3.put_object(Bucket=BUCKET_NAME, Key=f"transformed-{image_id}", Body=buffer)
        return {"filename": f"transformed-{image_id}", "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/transformed-{image_id}"}
    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid token")
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="Credentials not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{image_id}")
async def get_image(image_id: str, token: str = Depends(oauth2_scheme)):
    try:
        response = cognito_client.get_user(
            AccessToken=token
        )
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=image_id)
        return {"filename": image_id, "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{image_id}"}
    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid token")
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="Credentials not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images")
async def list_images(token: str = Depends(oauth2_scheme), page: int = 1, limit: int = 10):
    try:
        response = cognito_client.get_user(
            AccessToken=token
        )
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        if 'Contents' in response:
            images = [{"filename": obj["Key"], "size": obj["Size"]} for obj in response['Contents']]
            start = (page - 1) * limit
            end = start + limit
            return images[start:end]
        else:
            return []
    except cognito_client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid token")
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="Credentials not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create a handler for AWS Lambda
handler = Mangum(app)