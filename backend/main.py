from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import shutil
import os
import cv2
import numpy as np
import base64
import json

# Import your custom modules
from extractor import extract_frames
from embedder import VideoFingerprinter
from matcher import VideoMatcher

app = FastAPI()

# --- 1. GLOBAL SETUP (Run on Startup) ---
# Ensure all required folders exist immediately
os.makedirs("temp_videos", exist_ok=True)
os.makedirs("temp_frames", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount the static folder globally so React can stream the official video
app.mount("/static", StaticFiles(directory="static"), name="static")

# Enable CORS so React (localhost:3000) can talk to FastAPI (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the ML models
print("🚀 Loading AI Models...")
fingerprinter = VideoFingerprinter()
matcher = VideoMatcher(vector_dimension=2048)
print("✅ AI Detective System Online.")


# --- 2. ENDPOINTS ---

@app.post("/vault/upload/")
async def upload_official_video(file: UploadFile = File(...)):
    """Locks the official asset into the Vault and prepares it for streaming."""
    vid_path = f"static/official_source.mp4"  # We save it directly to static for the UI
    frame_dir = f"temp_frames/official_vault"

    with open(vid_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    frame_paths = extract_frames(vid_path, frame_dir)
    embeddings = [fingerprinter.get_embedding(p) for p in frame_paths]
    matcher.add_official_video(file.filename, embeddings)

    return {"status": "Success", "message": f"Asset '{file.filename}' secured."}


@app.websocket("/ws/scan/")
async def websocket_scan(websocket: WebSocket):
    """
    PRODUCTION SCANNER: Accepts live Base64 frame streams, processes in RAM,
    and returns actual ML confidence scores instantly.
    """
    await websocket.accept()

    try:
        while True:
            # 1. Receive the live frame from the React video player
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)

            if data.get("action") == "stop":
                break

            # Decode the base64 image string back into a NumPy array for OpenCV/PyTorch
            encoded_data = data["frame"].split(',')[1]
            nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Save temporarily just for the embedder (you can optimize this later to pass RAM directly to PyTorch)
            temp_frame_path = "temp_frames/live_mem_frame.jpg"
            cv2.imwrite(temp_frame_path, img)

            # --- THE ACTUAL AI MATH ---
            vec = fingerprinter.get_embedding(temp_frame_path)
            result = matcher.query_suspect_frame(vec, threshold=0.85)  # 85% confidence

            # 2. Fire the REAL data back to the frontend
            if result["match_found"]:
                official_time_ms = (result["matched_frame_number"] / 30) * 1000
                await websocket.send_json({
                    "match": True,
                    "confidence": float(result['confidence']),  # Send the raw math float
                    "official_seek_time": official_time_ms,
                    "timestamp": data["timestamp"]
                })
            else:
                await websocket.send_json({
                    "match": False,
                    "confidence": float(result.get('confidence', 0.0)),
                    "timestamp": data["timestamp"]
                })

    except WebSocketDisconnect:
        print("UI stream closed.")
    except Exception as e:
        print(f"Stream error: {e}")