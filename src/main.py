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
from fastapi import FastAPI, HTTPException
import boto3
from botocore.exceptions import NoCredentialsError
from mangum import Mangum
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Initialize the S3 client
s3 = boto3.client('s3')
BUCKET_NAME = os.getenv('BUCKET_NAME')

@app.get("/list-s3-objects/")
async def list_s3_objects():
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        if 'Contents' in response:
            return [{"filename": obj["Key"], "size": obj["Size"]} for obj in response['Contents']]
        else:
            return []
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="Credentials not available")

# Create a handler for AWS Lambda
handler = Mangum(app)