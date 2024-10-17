import io
import json
import os
import boto3
from PIL import Image
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
ENVIRONMENT = os.getenv('ENVIRONMENT', 'nonprod').lower()
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BUCKET_NAME = os.getenv('BUCKET_NAME_NONPROD')
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN_NONPROD')

# Initialize AWS clients
s3 = boto3.client('s3', region_name=AWS_REGION)
sns_client = boto3.client('sns', region_name=AWS_REGION)

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    if not SNS_TOPIC_ARN:
        logger.warning(f"SNS_TOPIC_ARN for {ENVIRONMENT} environment is not set")
        return {
            "statusCode": 500,
            "body": json.dumps(f"SNS Topic ARN for {ENVIRONMENT} environment is not configured")
        }

    try:
        process_record(event)
    except Exception as e:
        logger.error(f"Error processing record: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }

    return {
        "statusCode": 200,
        "body": json.dumps(f"Image processing completed in {ENVIRONMENT} environment")
    }

def process_record(message):
    logger.info(f"Processing record: {json.dumps(message)}")

    if 'filename' not in message:
        logger.error("No filename found in the message")
        raise ValueError("No filename provided in the event")

    filename = message['filename']
    operations = message.get('operations', [])

    # Fetch the image from S3
    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=filename)
        image = Image.open(io.BytesIO(obj['Body'].read()))
    except Exception as e:
        logger.error(f"Error fetching image from S3: {str(e)}")
        raise

    # Process operations
    for op in operations:
        if op['operation'] == 'resize':
            width = op.get('width', 100)
            height = op.get('height', 100)
            image = image.resize((width, height))

    # Save the transformed image back to S3
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    transformed_key = f"resized-{filename}"
    try:
        s3.put_object(Bucket=BUCKET_NAME, Key=transformed_key, Body=buffer)
    except Exception as e:
        logger.error(f"Error saving resized image to S3: {str(e)}")
        raise

    # Publish a message to SNS
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps({
                "filename": transformed_key,
                "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{transformed_key}",
                "operations": operations,
                "status": "completed",
                "environment": ENVIRONMENT
            })
        )
    except Exception as e:
        logger.error(f"Error publishing to SNS: {str(e)}")
        raise

    logger.info(f"Successfully processed {filename}")
