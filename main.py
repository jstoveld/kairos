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
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import boto3
from botocore.exceptions import NoCredentialsError
from PIL import Image, ImageOps, ImageFilter
import io


## Read Secret Key
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("No SECRET_KEY set for FastAPI application")


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


app = FastAPI()


## OAuth2PasswordBearer is a class that gets the tocken from the request
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


## Dummy User Data
fake_users_db = {
        "user@example.com": {
        "username": "user",
        "full_name": "John Doe",
        "email": "user@example.com",
        "hashed_password": "fakehashedpassword",
        "disabled": False,
    }
}

def verify_password(plain_password, hashed_password):
    return plain_password == hashed_password


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return user_dict
    

def authenticate_user(fake_db, email: str, password: str):
    user = get_user(fake_db, email)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.now(datetime.timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/token", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="Incorrect username or password",
            headers = {"WWW-Authenticate": "Bearer"}
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username)
    if user is None:
        raise credentials_exception
    return user


## Initialize s3 here
s3 = boto3.client('s3')
BUCKET_NAME = "kairos-images-landing-spot"


## Image Management Endpoints
@app.post("/images/")
async def upload_image(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    try:
        s3.upload_fileobj(file.file, BUCKET_NAME, file.filename)
        return {"filename": file.filename, "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{file.filename}"}
    except NoCredentialsError:
        return HTTPException(status_code=500, detail="Credentials not available")
    

@app.post("/images/resize/")
async def resize_image(width: int, height: int, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    try:
        image = Image.open(file.file)
        resized_image = image.resize((width, height))
        buffer = io.BytesIO()
        resized_image.save(buffer, format="JPEG")
        buffer.seek(0)
        s3.upload_fileobj(buffer, BUCKET_NAME, f"resized_{file.filename}")
        return {"filename": f"resuzed_{file.filename}", "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/resized_{file.filename}"}
    except NoCredentialsError:
        return HTTPException(status_code=500, detail="Credentials not available")
    

@app.post("/images/rotate/")
async def rotate_image(degrees: int, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    try:
        image = Image.open(file.file)
        rotated_image = image.rotate(degrees)
        buffer = io.BytesIO()
        rotated_image.save(buffer, format="JPEG")
        buffer.seek(0)
        s3.upload_fileobj(buffer, BUCKET_NAME, f"rotated_{file.filename}")
        return {"filename": f"rotated_{file.filename}", "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/rotated_{file.filename}"}
    except NoCredentialsError:
        return HTTPException(status_code=500, detail="Credentials not available")
    
app.get("/images/")
async def get_images(current_user: dict = Depends(get_current_user)):
    try:
        response = s3.list_objects_v2(bucket=BUCKET_NAME)
        if 'Contents' in response:
            return [{"filename": obj["key"], f"url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{obj["key"]}"} for obj in response['Contents']]
        else:
            return []
    except NoCredentialsError:
        return HTTPException(status_code=500, detail="Credentials not available")

