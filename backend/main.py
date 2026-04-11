from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import shutil
import os
import cv2
import numpy as np
import base64
import json

from extractor import extract_frames
from embedder import VideoFingerprinter
from matcher import VideoMatcher

app = FastAPI()

os.makedirs("temp_videos", exist_ok=True)
os.makedirs("temp_frames", exist_ok=True)
os.makedirs("static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("🚀 Loading AI Models...")
fingerprinter = VideoFingerprinter()
matcher = VideoMatcher(vector_dimension=2048)
OFFICIAL_FPS = 30.0  # Global variable to hold true FPS
print("✅ AI Detective System Online.")

@app.post("/vault/upload/")
async def upload_official_video(file: UploadFile = File(...)):
    global OFFICIAL_FPS
    vid_path = f"static/official_source.mp4"
    frame_dir = f"temp_frames/official_vault"

    with open(vid_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Detect exact FPS for perfect math sync later
    cap = cv2.VideoCapture(vid_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps > 0:
        OFFICIAL_FPS = fps
    cap.release()
    print(f"Vault Asset Locked. True Framerate: {OFFICIAL_FPS} FPS")

    frame_paths = extract_frames(vid_path, frame_dir)
    embeddings = [fingerprinter.get_embedding(p) for p in frame_paths]
    matcher.add_official_video(file.filename, embeddings)

    return {"status": "Success", "message": f"Asset secured at {OFFICIAL_FPS} FPS."}

@app.websocket("/ws/scan/")
async def websocket_scan(websocket: WebSocket):
    global OFFICIAL_FPS
    await websocket.accept()

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)

            if data.get("action") == "finalize":
                await websocket.send_json({
                    "status": "Complete",
                    "verdict": "DP SEQUENCE ALIGNMENT COMPLETE. CONFIDENCE SCORE AGGREGATED."
                })
                break

            try:
                encoded_data = data["frame"].split(',')[1]
                nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                temp_frame_path = "temp_frames/live_mem_frame.jpg"
                cv2.imwrite(temp_frame_path, img)

                # UI Visualization - Canny Edge Skeleton
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                edges = cv2.Canny(blurred, 50, 150)
                small = cv2.resize(edges, (112, 112))
                _, buffer = cv2.imencode('.jpg', small)
                neural_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

                vec = fingerprinter.get_embedding(temp_frame_path)
                result = matcher.query_suspect_frame(vec, threshold=0.65)

                raw_confidence = float(result.get('confidence', 0.0))

                if result.get("match_found"):
                    # The extractor pulls 1 frame per second.
                    # Therefore, FAISS index 5 = exactly 5.0 seconds into the video.
                    official_time_ms = result["matched_frame_number"] * 1000.0

                    await websocket.send_json({
                        "match": True,
                        "confidence": raw_confidence,
                        "official_seek_time": official_time_ms,
                        "matched_frame": result["matched_frame_number"],
                        "neural_vision": neural_b64
                    })
                else:
                    await websocket.send_json({
                        "match": False,
                        "confidence": raw_confidence,
                        "neural_vision": neural_b64
                    })

            except Exception as e:
                print(f"Backend Error: {str(e)}")
                await websocket.send_json({"error": f"TENSOR ERROR: {str(e)}"})

    except WebSocketDisconnect:
        print("UI stream closed.")