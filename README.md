# kairos
Backend image processor

**Kairos**: A Greek word meaning "opportune moment" or "key moment," implying a solution that
helps users seize the perfect image.

**Instructions**
https://roadmap.sh/projects/image-processing-service

Image Management API
This API allows users to register, log in, and manage images. Users can upload images, perform various transformations, and retrieve images in different formats. The API is secured with JWT authentication.

Requirements
Authentication
Users need to be able to create an account.
Users need to be able to log in.
Secure endpoints with JWT.
Image Management
Users must be able to upload images.
Users must be able to perform various operations on images:
Resize
Crop
Rotate
Watermark
Flip
Mirror
Compress
Change format (JPEG, PNG, etc.)
Apply filters (grayscale, sepia, etc.)
Retrieve a saved image in different formats:
PNG
JPEG
WEBP
List all uploaded images by a user with metadata.
Checklist
Rate limiting to prevent abuse.
Caching images to improve performance.
Error handling and validation.
Message queue to process image transformations asynchronously.
API Endpoints
Authentication Endpoints
Register a New User
Endpoint: POST /register

Description: Registers a new user.

Request Body:

Response:

Login an Existing User
Endpoint: POST /token

Description: Logs in an existing user and returns a JWT token.

Request Body:

Response:

1 vulnerability
Image Management Endpoints
Upload an Image
Endpoint: POST /images

Description: Uploads an image.

Request Body:

file: Select an image file to upload.
Response:

Apply Transformation to an Image
Endpoint: POST /images/{image_id}/transform

Description: Applies a transformation to an image.

Request Parameters:

image_id (path parameter): The ID (filename) of the image to transform.
Request Body:

Response:

Retrieve an Image
Endpoint: GET /images/{image_id}

Description: Fetches the details of an image stored in the S3 bucket, including its URL, size, content type, and last modified date.

Request Parameters:

image_id (path parameter): The ID (filename) of the image to fetch.
Response:

List All Uploaded Images
Endpoint: GET /images

Description: Gets a paginated list of all images uploaded by a user.

Query Parameters:

page: Page number (default is 1).
limit: Number of images per page (default is 10).
Response:

Additional Endpoints
Get User Info
Endpoint: GET /users/me

Description: Fetches the authenticated user's information.

Response:

List S3 Objects
Endpoint: GET /list-s3-objects/

Description: Lists all objects in the S3 bucket.

Response:

Error Handling
The API uses standard HTTP status codes to indicate the success or failure of an API request. The following are some common status codes:

200 OK: The request was successful.
400 Bad Request: The request could not be understood or was missing required parameters.
401 Unauthorized: Authentication failed or user does not have permissions for the requested operation.
404 Not Found: The requested resource could not be found.
500 Internal Server Error: An error occurred on the server.
Environment Variables
Ensure the following environment variables are set in your .env file:

BUCKET_NAME: The name of your S3 bucket.
COGNITO_USER_POOL_ID: The ID of your Cognito User Pool.
COGNITO_APP_CLIENT_ID: The Client ID of your Cognito App.
SECRET_KEY: The secret key used for JWT encoding.
ALGORITHM: The algorithm used for JWT encoding (default is HS256).
ACCESS_TOKEN_EXPIRE_MINUTES: The expiration time for access tokens (default is 30 minutes).
Running the Application
Install dependencies:

Run the application:

Access the API documentation: Open your browser and navigate to http://localhost:8000/docs to view the interactive API documentation.

Conclusion
This API provides a comprehensive solution for user authentication and image management, including uploading, transforming, and retrieving images. Ensure to handle authentication tokens securely and configure your environment variables correctly.

If you have any further questions or need additional assistance, feel free to ask!