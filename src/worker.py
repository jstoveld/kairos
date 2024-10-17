import os
import json
import boto3
from PIL import Image, ImageOps
import io
from dotenv import load_dotenv
import logging
from config import load_config

# Initialize Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Load configuration
config = load_config()

# Get environment variables
ENVIRONMENT = os.getenv('ENVIRONMENT', 'nonprod')
QUEUE_URL = os.getenv(f'SQS_QUEUE_URL_{ENVIRONMENT.upper()}')
AWS_REGION = os.getenv('AWS_REGION')
BUCKET_NAME = os.getenv(f'BUCKET_NAME_{ENVIRONMENT.upper()}')
LAMBDA_FUNCTION_NAME = os.getenv('LAMBDA_FUNCTION_NAME')

# Initialize AWS clients
sqs = boto3.client('sqs', region_name=AWS_REGION)
s3 = boto3.client('s3')
lambda_client = boto3.client('lambda', region_name=AWS_REGION)

if not QUEUE_URL:
    raise ValueError(f"Missing SQS queue URL for {ENVIRONMENT} environment")

def process_image(image, operations):
    for operation in operations:
        if operation['operation'] == 'resize':
            image = image.resize((operation['width'], operation['height']))
        elif operation['operation'] == 'rotate':
            image = image.rotate(operation['degrees'])
        elif operation['operation'] == 'grayscale':
            image = ImageOps.grayscale(image)
        # Add more operations as needed
    return image

def process_message_locally(message_body):
    image_id = message_body['image_id']
    operations = message_body['operations']

    try:
        # Get image from S3
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=image_id)
        image = Image.open(io.BytesIO(obj['Body'].read()))

        # Process image
        processed_image = process_image(image, operations)

        # Save processed image back to S3
        buffer = io.BytesIO()
        processed_image.save(buffer, format="PNG")
        buffer.seek(0)
        s3.put_object(Bucket=BUCKET_NAME, Key=f"processed-{image_id}", Body=buffer)

        logger.info(f"Successfully processed image: {image_id}")
        return True
    except Exception as e:
        logger.error(f"Error processing image {image_id}: {str(e)}")
        return False

def invoke_lambda(payload):
    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        return_payload = json.loads(response['Payload'].read())
        logger.info(f"Lambda response: {return_payload}")
        return return_payload.get('statusCode') == 200
    except Exception as e:
        logger.error(f"Error invoking Lambda: {str(e)}")
        return False

def main():
    logger.info(f"Starting worker for {ENVIRONMENT} environment")

    while True:
        try:
            logger.info(f"Attempting to receive messages from queue: {QUEUE_URL}")

            # Receive message from SQS queue
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )
            logger.debug(f"Receive message response: {response}")

            # Process messages
            if 'Messages' in response:
                for message in response['Messages']:
                    message_body = json.loads(message['Body'])
                    logger.info(f"Processing message: {message_body}")

                    # Decide whether to process locally or invoke Lambda
                    if LAMBDA_FUNCTION_NAME:
                        success = invoke_lambda(message_body)
                    else:
                        success = process_message_locally(message_body)

                    if success:
                        # Delete the processed message from the queue
                        sqs.delete_message(
                            QueueUrl=QUEUE_URL,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                        logger.info(f"Processed and deleted message: {message['MessageId']}")
                    else:
                        logger.error(f"Failed to process message: {message['MessageId']}")
            else:
                logger.info("No messages received.")
        except Exception as e:
            logger.error(f"Error receiving/processing message: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
