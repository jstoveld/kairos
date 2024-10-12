import boto3
from PIL import Image
import io
import json
import os

# Load environment variables
ENVIRONMENT = os.getenv('ENVIRONMENT', 'nonprod')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BUCKET_NAME = os.getenv('BUCKET_NAME_NONPROD') if ENVIRONMENT == 'nonprod' else os.getenv('BUCKET_NAME')
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')

# Initialize AWS clients
s3 = boto3.client('s3', region_name=AWS_REGION)
sns_client = boto3.client('sns', region_name=AWS_REGION)

def lambda_handler(event, context):
    for record in event['Records']:
        message = json.loads(record['body'])
        filename = message['filename']
        
        # Fetch the image from S3
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=filename)
        image = Image.open(io.BytesIO(obj['Body'].read()))

        # Perform the resize transformation
        image = image.resize((100, 100))

        # Save the transformed image back to S3
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        transformed_key = f"resized-{filename}"
        s3.put_object(Bucket=BUCKET_NAME, Key=transformed_key, Body=buffer)
        
        # Publish a message to SNS
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps({
                "filename": transformed_key,
                "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{transformed_key}",
                "operation": "resize",
                "status": "completed"
            })
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps(f"Resized image saved as {transformed_key}")
        }