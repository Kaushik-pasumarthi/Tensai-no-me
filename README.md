🛡️ SportShield AI: Digital Asset Protection Radar
Next-Generation Spatiotemporal Fingerprinting for Live Digital Forensics.
Built for the Google Solution Challenge 2026.

📖 Overview
Digital video piracy costs the entertainment and sports broadcasting industry billions annually. Current anti-piracy solutions rely on legacy cryptographic hashing (pHash/MD5), which fails entirely when pirates apply simple evasion tactics like color filters, cropping, or horizontal flipping.

SportShield AI completely re-engineers piracy detection. Instead of hashing easily manipulated pixels, our solution uses Deep Learning (ResNet50) to extract the underlying structural geometry of the broadcast into 2048-dimensional tensors. By indexing these tensors in a FAISS Vector Vault, our system maintains a mathematical lock on copyright material, completely immune to pirate evasion tactics.

✨ Core Features
Spatiotemporal Tensor Extraction: Converts video frames into structural geometric matrices using PyTorch and ResNet50, defeating spatial distortion attacks.

Visual Sanitizer (CLAHE): Real-time OpenCV pipeline strips color-grading and normalizes extreme lighting before AI evaluation.

Live Mirror Bypass: Automatically detects horizontally flipped streams and corrects them in milliseconds.

Autonomous Headless Web Crawler: Bypasses strict browser CORS constraints using yt-dlp to proactively hunt piracy across YouTube and third-party sites.

Real-Time WebSocket Intercept: Scans suspected network streams frame-by-frame with zero-latency telemetry.

Explainable AI & Automated Legal Action: Integrates Google Gemini API to analyze specific tampering vectors (e.g., cropping, speed changes) and auto-generates court-admissible DMCA takedown notices.

🏗️ Architecture & Tech Stack
Our architecture is split into a scalable, serverless backend and an enterprise-grade React dashboard.

Backend (Python / Google Cloud Run)

FastAPI: High-performance async REST & WebSocket API.

PyTorch & Torchvision: Core Deep Learning engine (ResNet50).

FAISS (Meta): Millisecond L2 Distance Matrix calculation for vector similarity.

OpenCV: Computer vision preprocessing.

SQLite: Ephemeral telemetry and incident logging.

yt-dlp: Headless swarm bot for stream extraction.

Frontend (React.js)

Glassmorphism SOC HUD: Custom CSS architecture designed for compliance command centers.

HTML5 Canvas: Real-time client-side frame processing and WebSocket transmission.

Cloud & AI (Google Cloud)

Google Cloud Run: Scale-to-zero serverless containerization.

Google Cloud Storage: Persistent storage for SQLite state and FAISS indices.

Google Gemini API: Generative legal forensics.

🚀 Local Setup & Installation
1. Clone the Repository
Bash
git clone https://github.com/yourusername/sportshield-ai.git
cd sportshield-ai
2. Backend Setup (FastAPI + AI Engine)
Ensure you have Python 3.9+ installed.

Bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
Note: You will need a .env file in the backend directory containing your Gemini API key:
GEMINI_API_KEY=your_google_ai_studio_key

Run the backend server:

Bash
uvicorn main:app --reload --port 8000
3. Frontend Setup (React Dashboard)
Ensure you have Node.js installed.

Bash
cd ../frontend
npm install
npm start
The application will launch at http://localhost:3000.

💻 Usage Guide
Secure Vault Upload: Navigate to the [1] SECURE VAULT UPLOAD card. Upload an official broadcaster MP4. The system will process the video, generate the tensor embeddings, and secure them in the local FAISS index.

Internet Feed Scanner: Navigate to the [2] INTERNET FEED SCANNER card. Paste a suspected .mp4 or .m3u8 network stream URL, or upload a local suspect file. Click Execute Scan. Watch the live WebSocket telemetry align the tensors and output a similarity score.

Autonomous Web Crawler: Navigate to [3] AUTONOMOUS WEB CRAWLER. Enter a keyword (e.g., "Dewald Brevis Six") and click Sweep. The headless bots will extract the top 3 YouTube results, bypass CORS, scan them against the vault, and log infringements to the database.

Generate DMCA (Gemini): Upon a successful lock, the backend utilizes the Gemini API to analyze the matched frames and generate a pre-formatted legal takedown draft.
