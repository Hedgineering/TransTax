from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])
socketio = SocketIO(app, cors_allowed_origins="*")

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on available packages. see https://stackoverflow.com/a/34598238
async_mode = None

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

connected_users = {}


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


def handle_pdf_generation(request_sid):
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
    print("Received request to generate PDFs:", data)
    # Start the PDF generation process in a separate thread to avoid blocking
    # Pass the client's session ID to target messages to the right client
    threading.Thread(target=handle_pdf_generation, args=(request.sid,)).start()
    # handle_pdf_generation(request.sid)


if __name__ == "__main__":
    socketio.run(app, debug=True)
