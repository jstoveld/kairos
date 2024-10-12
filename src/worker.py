import os
import json
import boto3
from PIL import Image, ImageOps
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Get environment variables
ENVIRONMENT = os.getenv('ENVIRONMENT', 'nonprod')
QUEUE_URL = os.getenv(f'SQS_QUEUE_URL_{ENVIRONMENT.upper()}')
AWS_REGION = os.getenv(f'AWS_REGION')

BUCKET_NAME = os.getenv('BUCKET_NAME')

# Initialize AWS clients
sqs = boto3.client('sqs', region_name=AWS_REGION)
s3 = boto3.client('s3')

if not QUEUE_URL:
    raise ValueError(f"Missing SQS queue URL for {ENVIRONMENT} environment")

def process_image(image, operations):
    for operation in operations:
        if operation['type'] == 'resize':
            image = image.resize((operation['width'], operation['height']))
        elif operation['type'] == 'rotate':
            image = image.rotate(operation['degrees'])
        elif operation['type'] == 'grayscale':
            image = ImageOps.grayscale(image)
        # Add more operations as needed
    return image

def process_message(message):
    body = json.loads(message['Body'])
    image_id = body['image_id']
    operations = body['operations']

    try:
        # Get image from S3
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=image_id)
        image = Image.open(io.BytesIO(obj['Body'].read()))

        # Process image
        processed_image = process_image(image, operations)

        # Save processed image back to S3
        buffer = io.BytesIO()
        processed_image.save(buffer, format="JPEG")
        buffer.seek(0)
        s3.put_object(Bucket=BUCKET_NAME, Key=f"processed-{image_id}", Body=buffer)

        print(f"Successfully processed image: {image_id}")
    except Exception as e:
        print(f"Error processing image {image_id}: {str(e)}")

def main():
    print(f"Starting worker for {ENVIRONMENT} environment")
    while True:
        try:
            # Receive message from SQS queue
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )

            # Process messages
            if 'Messages' in response:
                for message in response['Messages']:
                    process_message(message)
                    
                    # Delete the processed message from the queue
                    sqs.delete_message(
                        QueueUrl=QUEUE_URL,
                        ReceiptHandle=message['ReceiptHandle']
                    )
        except Exception as e:
            print(f"Error receiving/processing message: {str(e)}")

if __name__ == "__main__":
    main()
