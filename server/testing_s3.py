import boto3
from botocore.exceptions import ClientError
import os
import time
from dotenv import load_dotenv

load_dotenv()


def delete_file_from_s3(s3_client, bucket_name, object_name):
    """
    Delete a file from an S3 bucket

    :param s3_client: Initialized S3 client
    :param bucket_name: Name of the bucket from which to delete the file
    :param object_name: Name of the object to delete
    :return: None
    """
    try:
        response = s3_client.delete_object(Bucket=bucket_name, Key=object_name)
        print(f'Successfully deleted {object_name} from {bucket_name}')
    except Exception as e:
        print(f"An error occurred: {e}")


def upload_file(s3_client, file_name, bucket_name, object_name=None):
    """
    Upload a file to an S3 bucket

    :param s3_client: Initialized S3 client
    :param file_name: File to upload
    :param bucket_name: Bucket to upload to
    :param object_name: S3 object name. If not specified, file_name is used
    :return: None
    """
    # If S3 object_name was not specified, use the file name as object name
    if object_name is None:
        object_name = os.path.basename(file_name)

    try:
        # Perform the upload
        s3_client.upload_file(file_name, bucket_name, object_name)
        print(f'Successfully uploaded {file_name} to {bucket_name}/{object_name}')
    except FileNotFoundError:
        print("The file was not found")
    except Exception as e:
        print(f"An error occurred: {e}")

def create_presigned_url(bucket_name, object_name, expiration=60):
    """
    Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """
    # Get AWS credentials from environment variables
    access_id = os.getenv('ACCESS_ID')
    access_key = os.getenv('ACCESS_KEY')

    # Create a boto3 client with the credentials
    s3_client = boto3.client('s3', aws_access_key_id=access_id, aws_secret_access_key=access_key)
    
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_name},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        print(f"An error occurred: {e}")
        return None

    return response

if __name__ == "__main__":
    BUCKET_NAME = os.environ['BUCKET_NAME'] 
    ACCESS_ID= os.environ['ACCESS_ID'] 
    ACCESS_KEY = os.environ['ACCESS_KEY'] 

    s3 = boto3.client('s3',
                      aws_access_key_id=ACCESS_ID,
                      aws_secret_access_key= ACCESS_KEY)
    buckets_resp = s3.list_buckets()
    for bucket in buckets_resp['Buckets']:
        print(bucket)

    base_filename="Invoice_C600470331_en_to_es.pdf"
    file_to_upload = "./generated/Invoice_C600470331_en_to_es.pdf"
    object_name = file_to_upload[-len(base_filename):] #change so that it works for each filename
    # Upload file to s3 bucket
    upload_file(s3, file_to_upload, BUCKET_NAME)

    print("Generating Pre-signed url...")

    # Generate a presigned URL for the object
    url = create_presigned_url(BUCKET_NAME, object_name)

    if url:
        print(f"Presigned URL to download {object_name}: {url}")
    else:
        print("Failed to generate URL")

    print("will delete file from cloud in 65 seconds...")
     # Wait for 1 minute before deleting the file
    time.sleep(65)  # Delay set for 60 seconds

    # Call the function to delete the file from S3
    delete_file_from_s3(s3, BUCKET_NAME, object_name)