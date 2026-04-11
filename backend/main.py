from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import shutil
import os
import cv2
import numpy as np
import base64
import json
from pydantic import BaseModel
import yt_dlp
from extractor import extract_frames
from embedder import VideoFingerprinter
from matcher import VideoMatcher
import sqlite3
class YTRequest(BaseModel):
    url: str
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

# --- INITIALIZE DATABASE ---
conn = sqlite3.connect("violations.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS violations
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                   vault_asset TEXT,
                   matched_frame INTEGER,
                   confidence REAL,
                   source_type TEXT)''')
conn.commit()
print("✅ Digital Forensics Database Online.")


@app.post("/vault/upload/")
async def upload_official_video(file: UploadFile = File(...)):
    global OFFICIAL_FPS
    global matcher  # <--- Bring in the global AI database

    # REBOOT THE AI MEMORY: Wipe out any previous videos
    matcher = VideoMatcher(vector_dimension=2048)

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
    session_logged = False  # <--- Add this flag

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
                result = matcher.query_suspect_frame(vec, base_min_threshold=0.65)

                raw_confidence = float(result.get('confidence', 0.0))

                if result.get("match_found"):

                    # --- CORRECT MATH APPLIED HERE ---
                    # 1 extracted frame = exactly 1 full second
                    official_time_ms = float(result["matched_frame_number"] * 1000.0)

                    # --- WRITE TO DATABASE ONCE PER SESSION ---
                    if not session_logged:
                        cursor.execute(
                            "INSERT INTO violations (vault_asset, matched_frame, confidence, source_type) VALUES (?, ?, ?, ?)",
                            (result["matched_video"], result["matched_frame_number"], raw_confidence,
                             "INTERNET_STREAM"))
                        conn.commit()
                        session_logged = True
                        print(
                            f"🚨 VIOLATION LOGGED: {result['matched_video']} at Frame {result['matched_frame_number']}")

                    await websocket.send_json({
                        "match": True,
                        "confidence": raw_confidence,
                        "threshold": result.get("adaptive_threshold", 0.65),  # Safely grab dynamic threshold
                        "official_seek_time": official_time_ms,
                        "matched_frame": result["matched_frame_number"],
                        "neural_vision": neural_b64
                    })
                else:
                    await websocket.send_json({
                        "match": False,
                        "confidence": raw_confidence,
                        "threshold": result.get("adaptive_threshold", 0.65),  # <--- ADD THIS LINE
                        "neural_vision": neural_b64
                    })

            except Exception as e:
                print(f"Backend Error: {str(e)}")
                await websocket.send_json({"error": f"TENSOR ERROR: {str(e)}"})

    except WebSocketDisconnect:
        print("UI stream closed.")


@app.post("/scan/youtube/")
async def scan_youtube_url(req: YTRequest):
    global matcher, fingerprinter

    ydl_opts = {'format': 'best[ext=mp4]', 'quiet': True}
    try:
        # 1. Bypass Google's CORS and rip the raw stream URL
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            stream_url = info['url']

        # 2. Connect OpenCV directly to the web stream
        cap = cv2.VideoCapture(stream_url)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps is None:
            fps = 30.0

        frame_skip = int(fps)  # Jump 1 full second at a time to scan fast

        frame_count = 0
        max_seconds_to_scan = 30  # For demo purposes, only scan the first 30 seconds

        # 3. Scan the stream headlessly
        while cap.isOpened() and frame_count < max_seconds_to_scan:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count * frame_skip)
            ret, frame = cap.read()
            if not ret:
                break

            temp_path = "temp_frames/yt_temp.jpg"
            cv2.imwrite(temp_path, frame)

            # Pass through ResNet50 and FAISS
            vec = fingerprinter.get_embedding(temp_path)
            result = matcher.query_suspect_frame(vec, base_min_threshold=0.85)
            if result.get("match_found"):
                cap.release()

                # Log the YouTube violation to the Database!
                cursor.execute(
                    "INSERT INTO violations (vault_asset, matched_frame, confidence, source_type) VALUES (?, ?, ?, ?)",
                    (result["matched_video"], result["matched_frame_number"], float(result["confidence"]),
                     "YOUTUBE_CRAWLER")
                )
                conn.commit()
                print(f"🚨 YOUTUBE VIOLATION LOGGED: {req.url}")

                return {
                    "status": "Match Found",
                    "youtube_second": frame_count,
                    "vault_asset": result["matched_video"],
                    "vault_frame": result["matched_frame_number"],
                    "confidence": float(result["confidence"])
                }

            frame_count += 1

        cap.release()
        return {"status": "No Match", "message": f"Scanned first {max_seconds_to_scan} seconds. No piracy detected."}

    except Exception as e:
        print(f"YouTube Scan Error: {str(e)}")
        return {"error": str(e)}