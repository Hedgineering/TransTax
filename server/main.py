# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on available packages. see https://stackoverflow.com/a/34598238
async_mode = None

from InvoiceGenerator import generate_invoice

# if async_mode is None:
#     try:
#         import eventlet

#         async_mode = "eventlet"
#     except ImportError:
#         pass

#     if async_mode is None:
#         try:
#             from gevent import monkey

#             async_mode = "gevent"
#         except ImportError:
#             pass

#     if async_mode is None:
#         async_mode = "threading"

#     print("async_mode is " + async_mode)

# monkey patching is necessary because this application uses a background
# thread
# if async_mode == "eventlet":
#     import eventlet

#     eventlet.monkey_patch()
# elif async_mode == "gevent":
#     from gevent import monkey

#     monkey.patch_all()

from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit, send
from flask_cors import CORS
import threading
import os
import base64
import time
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()
BUCKET_NAME = os.environ['BUCKET_NAME'] 
ACCESS_ID= os.environ['ACCESS_ID'] 
ACCESS_KEY = os.environ['ACCESS_KEY'] 
s3 = boto3.client('s3',
                    aws_access_key_id=ACCESS_ID,
                    aws_secret_access_key= ACCESS_KEY)
buckets_resp = s3.list_buckets()
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])
socketio = SocketIO(app, cors_allowed_origins="*")

connected_users = {}
upload_path = "uploads"


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'zip', 'csv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

file_chunks = {}


@socketio.on("file_chunk")
def handle_file_chunk(data):
    # Extracting the chunk data
    file_id = data["fileId"]
    chunk_index = data["chunkIndex"]
    total_chunks = data["totalChunks"]
    chunk_data = base64.b64decode(data["chunkData"])
    file_name = data["fileName"]  # Consider sanitizing this

    # Initialize the file's chunk list if not already
    if file_id not in file_chunks:
        file_chunks[file_id] = [None] * total_chunks

    # Store the chunk data
    file_chunks[file_id][chunk_index] = chunk_data

    # Check if all chunks have been received
    if all(chunk is not None for chunk in file_chunks[file_id]):
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)

        # Sanitize the file_name or ensure it's safe before appending it to the path
        safe_file_name = os.path.join(upload_path, os.path.basename(file_name))

        # Reassemble the file
        with open(safe_file_name, "wb") as file:
            for chunk in file_chunks[file_id]:
                file.write(chunk)

        print(f"Received and reassembled {safe_file_name}")

        # Cleanup: remove stored chunks to free memory
        del file_chunks[file_id]


@socketio.on("connect")
def handle_connect():
    print(f"Client connected: {request.sid}")
    connected_users[request.sid] = "Connected"
    print(f"Clients: {connected_users}")
    socketio.emit("hello", to=request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    if request.sid in connected_users:
        del connected_users[request.sid]
    print(f"Clients: {connected_users}")

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
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

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

def handle_pdf_generation(request_sid, data):
    file_name = data['fileName']

    languages = {
        "arabic": "ar",
        "chinese": "zh",
        "english": "en",
        "french": "fr",
        "greek": "el",
        "hindi": "hi",
        "japanese": "ja",
        "korean": "ko",
        "russian": "ru",
        "spanish": "es",
    }

    source_language = languages[data["sourceLanguage"]]
    destination_language = languages[data["destinationLanguage"]]

    
    print(f"\n\nHandle pdf generation for {file_name}\n\n")

    # Sanitize the file_name or ensure it's safe before appending it to the path
    safe_file_name = os.path.join(upload_path, os.path.basename(file_name))

    if not os.path.exists(upload_path):
        print('upload path does not exist')
        return

    # Wait for the file to exist, with a timeout
    start_time = time.time()
    while not os.path.exists(safe_file_name):
        if time.time() - start_time > 5:  # Timeout after 5 seconds
            print('Timeout waiting for file to become available.')
            return
        time.sleep(0.1)  # Sleep for 100ms before checking again

    # At this point, safe_file_name exists or we've timed out
    if not os.path.isfile(safe_file_name):
        print('safe file name path exists but is not a file')
        return

    info = generate_invoice(filePath=safe_file_name, fileHeader=0, dest_language=destination_language)
    socketio.emit("pdf_ready", {"urls": info}, to=request_sid)

    # After all PDFs are "generated", notify the client that the job is finished
    # socketio.emit("job_finished", {"message": "All PDFs generated."}, to=request_sid)
    print(f"finished sending pdfs to {request_sid}")


@socketio.on("generate_pdfs")
def handle_generate_pdfs(data):
    print("\n\n======================================================")
    print(f"Source Language: {data['sourceLanguage']},")
    print(f"Source Currency: {data['sourceCurrency']},")
    print(f"Destination Language: {data['destinationLanguage']},")
    print(f"Destination Currency: {data['destinationCurrency']}")
    print(f"File Name: {data['fileName']}")
    print(f"File ID: {data['fileId']}")
    print("======================================================\n\n")
    print("Received request to generate PDFs:", data)
    # Start the PDF generation process in a separate thread to avoid blocking
    # Pass the client's session ID to target messages to the right client
    # threading.Thread(target=handle_pdf_generation, args=(request.sid, data)).start()
    handle_pdf_generation(request.sid,data)
    # handle_pdf_generation(request.sid)

@socketio.on('send_urls')
def send_url_links(data):
    urls = []
    generation_path = "generated"
    if os.path.exists(generation_path):
        for i in data['urls']:
            file_to_upload = os.path.join(os.getcwd(), generation_path, os.path.basename(i))
            object_name = i
            print(file_to_upload,object_name,'\n')
            upload_file(s3, file_to_upload, BUCKET_NAME)
            print("Generating Pre-signed url...")

            # Generate a presigned URL for the object
            url = create_presigned_url(BUCKET_NAME, object_name)

            if url:
                print(f"Presigned URL to download {object_name}: {url}")
                urls.append(url)
            else:
                print("Failed to generate URL")
        if(len(urls)==0):
            socketio.emit('file_error',{'error': "Couldn't generate urls"})
        else:
            socketio.emit('send_aws_urls',{'urls': urls}, to=request.sid)


if __name__ == "__main__":
    app.config['UPLOAD_FOLDER'] = 'uploads'
    socketio.run(app, debug=True)
