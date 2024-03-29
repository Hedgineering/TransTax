# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on available packages. see https://stackoverflow.com/a/34598238
async_mode = None

from InvoiceGenerator import generate_invoice

if async_mode is None:
    try:
        import eventlet

        async_mode = "eventlet"
    except ImportError:
        pass

    if async_mode is None:
        try:
            from gevent import monkey

            async_mode = "gevent"
        except ImportError:
            pass

    if async_mode is None:
        async_mode = "threading"

    print("async_mode is " + async_mode)

# monkey patching is necessary because this application uses a background
# thread
if async_mode == "eventlet":
    import eventlet

    eventlet.monkey_patch()
elif async_mode == "gevent":
    from gevent import monkey

    monkey.patch_all()

from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import os
import base64

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])
socketio = SocketIO(app, cors_allowed_origins="*")

connected_users = {}

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
        upload_path = "uploads"
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

@socketio.on('send_file')
def handle_file_send(data):
    print(data)
    file_data = data['file_data']  # Assuming base64 encoded or byte array
    filename = data['filename']
    if allowed_file(filename):
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'],exist_ok=True)
            with open(os.path.join(app.config['UPLOAD_FOLDER'],filename), 'wb') as f:
                f.write(file_data)
            emit('file_received', {'filename': filename, 'message': 'File uploaded successfully!'})
        except Exception as e:
            emit('file_error', {'error': str(e)})
    else:
        emit('file_error', {'error': 'Invalid file type'})

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

def handle_pdf_generation(request_sid, fileName):
    print(fileName)
    # Simulate busy work and generate placeholder PDF URLs
    placeholder_urls = [
        "http://example.com/pdf1.pdf",
        "http://example.com/pdf2.pdf",
        "http://example.com/pdf3.pdf",
    ]

    for idx, url in enumerate(placeholder_urls):
        # Using time.sleep or thread.sleep screws up socketio async event loop, use socketio.sleep() instead
        socketio.sleep(2)  # Simulate time taken to generate each PDF
        # Emit 'pdf_ready' event with URL, only to the client that made the request
        # socketio.emit("pdf_ready", {"url": url}, to=request_sid)
        socketio.emit("pdf_ready", {"url": url}, to=request_sid)
        print(f"sent pdf {idx+1} to client {request_sid}")

    # After all PDFs are "generated", notify the client that the job is finished
    socketio.emit("job_finished", {"message": "All PDFs generated."}, to=request_sid)
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
    threading.Thread(target=handle_pdf_generation, args=(request.sid, data['fileName'])).start()
    # handle_pdf_generation(request.sid)


if __name__ == "__main__":
    app.config['UPLOAD_FOLDER'] = 'uploads'
    socketio.run(app, debug=True)
