import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [vaultFile, setVaultFile] = useState(null);
  const [suspectSrc, setSuspectSrc] = useState(null);
  const [isVaultLocked, setIsVaultLocked] = useState(false);
  const [vaultTimestamp, setVaultTimestamp] = useState("");
  const [neuralVision, setNeuralVision] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isLocked, setIsLocked] = useState(false);
  const [matchConfidence, setMatchConfidence] = useState('');
  const [liveThreshold, setLiveThreshold] = useState(65.0); // <--- ADD THIS NEW STATE
  const [ytKeyword, setYtKeyword] = useState("");
  const [isSweeping, setIsSweeping] = useState(false);
  const [ytUrl, setYtUrl] = useState("");
  const [ytResult, setYtResult] = useState(null);
  const [isYtScanning, setIsYtScanning] = useState(false);
  const [liveConfidence, setLiveConfidence] = useState(0);
  const [targetFrame, setTargetFrame] = useState('STANDBY');
  const [internetUrl, setInternetUrl] = useState("");

  const [telemetryLogs, setTelemetryLogs] = useState(["SYSTEM INITIALIZED. WAITING FOR DIRECTIVE..."]);
  const [currentHash, setCurrentHash] = useState("AWAITING_TENSOR_INPUT...");
  const peakConfidenceRef = useRef(0);
  const suspectPlayerRef = useRef(null);
  const officialPlayerRef = useRef(null);
  const socketRef = useRef(null);
  const logsEndRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [telemetryLogs]);

  useEffect(() => {
    return () => {
      clearInterval(window.scanInterval);
      if (socketRef.current) socketRef.current.close();
    };
  }, []);

  useEffect(() => {
    let interval;
    if (isScanning && !isLocked) {
      interval = setInterval(() => {
        const hash1 = Math.random().toString(16).substr(2, 8).toUpperCase();
        const hash2 = Math.random().toString(16).substr(2, 8).toUpperCase();
        setCurrentHash(`[${hash1}-${hash2}]`);
      }, 100);
    }
    return () => clearInterval(interval);
  }, [isScanning, isLocked]);

  const addLog = (msg, type = "info") => {
    setTelemetryLogs(prev => [...prev, { time: new Date().toISOString().substring(11, 23), msg, type }]);
  };

  const handleVaultUpload = async () => {
    if (!vaultFile) return alert("Select reference asset.");
    addLog(`UPLOADING ${vaultFile.name} TO SECURE VAULT...`, "process");

    const formData = new FormData();
    formData.append('file', vaultFile);

    try {
      const response = await axios.post('https://thecapybara-sportshield-engine.hf.space/vault/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      addLog(`VAULT LOCKED: ${response.data.message}`, "info");
      addLog("FAISS VECTOR INDEX UPDATED.", "info");
      setIsVaultLocked(true);
      setVaultTimestamp(Date.now()); // Set URL hash exactly once
    } catch (error) {
      addLog("VAULT UPLOAD FAILED. CONNECTION SEVERED.", "alert");
    }
  };

  const startRealTimeScan = () => {
    if (!suspectSrc) return alert("Provide an internet feed file or URL.");

    setIsScanning(true);
    setIsLocked(false);
    setLiveConfidence(0);
    setMatchConfidence('');
    setTargetFrame("SCANNING...");
    peakConfidenceRef.current = 0; // Reset peak score for new scan

    suspectPlayerRef.current.load();
    officialPlayerRef.current.load();

    socketRef.current = new WebSocket("wss://thecapybara-sportshield-engine.hf.space/ws/scan/");

    socketRef.current.onopen = () => {
        addLog("SYSTEM SECURED: Establishing bi-directional tensor stream...", "process");
        // SAFE PLAY: Catch network buffering interruptions so React doesn't crash
        const playPromise = suspectPlayerRef.current.play();
        if (playPromise !== undefined) {
            playPromise.catch(error => {
                console.log("Stream buffering safely handled.");
            });
        }

        window.scanInterval = setInterval(() => {
            if (suspectPlayerRef.current && !suspectPlayerRef.current.paused) {
                const video = suspectPlayerRef.current;
                const canvas = canvasRef.current;
                const context = canvas.getContext('2d', { willReadFrequently: true });

                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                const frameData = canvas.toDataURL('image/jpeg', 0.5);

                socketRef.current.send(JSON.stringify({
                    frame: frameData,
                    timestamp: video.currentTime
                }));
            }
        }, 200);
    };

    socketRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.error) {
            addLog(data.error, "alert");
            return;
        }

        if (data.status === "Complete") {
            addLog(`FINAL VERDICT: ${data.verdict}`, "alert");
            setCurrentHash("ANALYSIS_COMPLETE");
            setIsLocked(false);
            setTargetFrame("SCAN TERMINATED");

            // --- THE NEW POP-UP LOGIC ---
            setTimeout(() => {
                if (peakConfidenceRef.current > 0) {
                    alert(`🚨 PIRACY DETECTED!\n\nThe system successfully matched this stream to your vault.\nPeak Confidence Score: ${(peakConfidenceRef.current * 100).toFixed(1)}%\n\nThe violation has been securely logged to the database.`);
                } else {
                    alert(`✅ STREAM CLEAR\n\nThe scan has concluded. No copyright infringement was detected in this video feed.`);
                }
            }, 500); // 500ms delay so the video finishes pausing smoothly
            // -----------------------------

            if (officialPlayerRef.current) officialPlayerRef.current.pause();
            if (suspectPlayerRef.current) suspectPlayerRef.current.pause();
            if (socketRef.current) socketRef.current.close();
            return;
        }

        const confPercent = (data.confidence * 100).toFixed(1);
        setLiveConfidence(confPercent);
        // --- ADD THIS: Update the live threshold if the backend sends it ---
        if (data.threshold) {
            setLiveThreshold((data.threshold * 100).toFixed(1));
        }

        if (data.neural_vision) setNeuralVision(data.neural_vision);

        const safePlay = (videoElement) => {
            if (videoElement && videoElement.paused) {
                const p = videoElement.play();
                if (p !== undefined) p.catch(() => {});
            }
        };

        if (data.match) {
            if (data.confidence > peakConfidenceRef.current) {
                peakConfidenceRef.current = data.confidence;
            }
            setIsLocked(true);
            setMatchConfidence(`${confPercent}%`);
            setCurrentHash(`FAISS_L2: ${data.confidence.toFixed(4)}`);
            setTargetFrame(`LOCKED ON VAULT FRAME: #${data.matched_frame}`);

            if (officialPlayerRef.current) {
                const targetTime = data.official_seek_time / 1000;
                const currentTime = officialPlayerRef.current.currentTime;
                const timeDiff = Math.abs(currentTime - targetTime);

                // Smart sync: don't stutter the video if it's already close
                if (timeDiff > 0.8 || officialPlayerRef.current.paused) {
                    officialPlayerRef.current.currentTime = targetTime;
                }
                safePlay(officialPlayerRef.current);
            }

        } else {
            setIsLocked(false);
            setCurrentHash(`CALCULATING...`);
            setTargetFrame(`SEARCHING FAISS INDEX...`);
            if (officialPlayerRef.current && !officialPlayerRef.current.paused) {
                officialPlayerRef.current.pause();
            }
        }
    };

    socketRef.current.onerror = (e) => addLog("WEBSOCKET STREAM INTERRUPTED.", "alert");
    socketRef.current.onclose = () => clearInterval(window.scanInterval);
  };

  const stopScan = () => {
    clearInterval(window.scanInterval);
    setIsScanning(false);
    if (suspectPlayerRef.current) suspectPlayerRef.current.pause();
    if (officialPlayerRef.current) officialPlayerRef.current.pause();
    socketRef.current?.send(JSON.stringify({ action: "stop" }));
    addLog("MANUAL OVERRIDE: SCAN TERMINATED.", "info");
  };

  const handleVideoEnd = () => {
    clearInterval(window.scanInterval);
    setIsScanning(false);

    if (suspectPlayerRef.current) suspectPlayerRef.current.pause();
    if (officialPlayerRef.current) officialPlayerRef.current.pause();

    addLog("END OF FEED REACHED. RUNNING DP SEQUENCE MATRIX...", "process");

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ action: "finalize" }));
    }
  };
const scanYouTube = async () => {
    if (!ytUrl) return alert("Paste a YouTube link first!");
    setIsYtScanning(true);
    setYtResult("Bypassing CORS & extracting headless stream...");

    try {
        const response = await fetch("https://thecapybara-sportshield-engine.hf.space/scan/youtube/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: ytUrl })
        });
        const data = await response.json();

        if (data.error) {
            setYtResult(`Error: ${data.error}`);
        } else {
            // Format the new metadata beautifully!
            const metaString = `📺 [${data.channel_name}]\n🎬 ${data.video_title}\n\n`;

            if (data.status === "Match Found") {
                setYtResult(`${metaString}🚨 TAKEDOWN TRIGGERED: Match found at 0:${data.youtube_second < 10 ? '0'+data.youtube_second : data.youtube_second}. Confidence: ${(data.confidence * 100).toFixed(1)}%`);
            } else {
                setYtResult(`${metaString}✅ CLEAR: ${data.message}`);
            }
        }
    } catch (err) {
        setYtResult("Network error connecting to backend.");
    }
    setIsYtScanning(false);
  };
const sweepYouTube = async () => {
    if (!ytKeyword) return alert("Enter a search keyword!");
    setIsSweeping(true);
    setYtResult(`Deploying bots for: "${ytKeyword}"...\nScanning top 3 results...`);

    try {
        const response = await fetch("https://thecapybara-sportshield-engine.hf.space/scan/youtube/search/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: ytKeyword })
        });
        const data = await response.json();

        if (data.error) {
            setYtResult(`Error: ${data.error}`);
        } else {
            // We only declare 'let' ONCE here
            let formattedResult = `Sweep Complete for "${ytKeyword}":\n\n`;

            data.results.forEach((res, index) => {
                const meta = `📺 [${res.channel}]\n🎬 ${res.title}`;
                if (res.status === "🚨 DETECTED") {
                    formattedResult += `[Rank ${index+1}] 🚨 PIRACY (${(res.confidence * 100).toFixed(1)}%)\n${meta}\n\n`;
                } else {
                    formattedResult += `[Rank ${index+1}] ✅ CLEAR\n${meta}\n\n`;
                }
            });
            setYtResult(formattedResult);
        }
    } catch (err) {
        setYtResult("Network error connecting to backend.");
    }
    setIsSweeping(false);
  };
return (
    <div className="dashboard">
{/* --- REVISED HEADER: TITLE ON LEFT, SMALL BUTTON ON RIGHT --- */}
      <header className="header" style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ flexShrink: 0 }}>
          <h1 style={{ margin: '0' }}>Digital Asset Protection Radar</h1>
          <p style={{ color: '#94a3b8', margin: '5px 0' }}>AI-Powered Spatiotemporal Fingerprinting Network</p>
        </div>
        
        {/* --- LOCKED WIDTH BUTTON --- */}
        <a 
          href="https://sport-shield-ai.onrender.com/" 
          target="_blank" 
          rel="noopener noreferrer"
          style={{ 
              display: 'inline-block',
              width: 'max-content',      /* Forces it to only be as wide as the text */
              flex: '0 0 auto',          /* Prevents flexbox from stretching it */
              whiteSpace: 'nowrap',      /* Keeps text on one line */
              textDecoration: 'none', 
              background: '#eab308', 
              color: '#000', 
              fontWeight: 'bold', 
              padding: '10px 24px', 
              borderRadius: '4px',
              fontSize: '14px',
              border: '2px solid #eab308',
              cursor: 'pointer'
          }}
        >
          RETURN TO DASHBOARD ↗
        </a>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '0 20px 20px 20px' }}>

        {/* --- TOP ROW: 3 Equal-Height Cards --- */}
        <div style={{ display: 'flex', gap: '20px', alignItems: 'stretch' }}>

            {/* Card 1 */}
            <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ marginTop: 0, color: '#60a5fa' }}>[1] SECURE VAULT UPLOAD</h3>
              <input type="file" accept="video/*" onChange={(e) => setVaultFile(e.target.files[0])} style={{ marginBottom: '15px' }} />
              <div style={{ marginTop: 'auto' }}>
                <button className="btn" onClick={handleVaultUpload} style={{ width: '100%' }}>ENCRYPT & STORE IN FAISS</button>
              </div>
            </div>

            {/* Card 2 */}
            <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ marginTop: 0, color: '#ef4444' }}>[2] INTERNET FEED SCANNER</h3>
              <div style={{ marginBottom: '10px' }}>
                  <span style={{ color: '#94a3b8', fontSize: '12px' }}>OPTION A: LOCAL FILE OVERRIDE</span>
                  <input type="file" accept="video/*" onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                          setSuspectSrc(URL.createObjectURL(e.target.files[0]));
                      }
                  }} style={{ width: '100%' }} />
              </div>
              <div style={{ marginBottom: '15px' }}>
                  <span style={{ color: '#94a3b8', fontSize: '12px' }}>OPTION B: REAL-TIME URL INTERCEPT</span>
                  <input
                      type="text"
                      placeholder="Paste Live Stream URL (.mp4, .m3u8)"
                      value={internetUrl}
                      onChange={(e) => {
                          setInternetUrl(e.target.value);
                          setSuspectSrc(e.target.value);
                      }}
                      style={{ width: '100%', padding: '8px', background: '#0f172a', border: '1px solid #334155', color: '#fff', marginTop: '5px', boxSizing: 'border-box' }}
                  />
              </div>
              <div style={{ display: 'flex', gap: '10px', marginTop: 'auto' }}>
                <button className={`btn ${isScanning ? 'btn-alert' : ''}`} onClick={startRealTimeScan} disabled={!suspectSrc} style={{ flex: 1 }}>
                  {isScanning ? "SCAN IN PROGRESS..." : "EXECUTE REAL-TIME DETECTIVE"}
                </button>
                {isScanning && (
                   <button className="btn btn-alert" style={{width: 'auto'}} onClick={stopScan}>HALT</button>
                )}
              </div>
            </div>

            {/* Card 3 */}
            <div className="card" style={{ flex: 1, borderTop: '2px solid #eab308', display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ marginTop: 0, color: '#eab308' }}>[3] AUTONOMOUS WEB CRAWLER</h3>
              <p style={{ color: '#94a3b8', fontSize: '12px', marginTop: '0', marginBottom: '10px' }}>
                Headless extraction. Bypasses CORS constraints.
              </p>

              <div style={{ marginBottom: '10px' }}>
                  <span style={{ color: '#94a3b8', fontSize: '12px' }}>OPTION A: DIRECT URL TARGETING</span>
                  <div style={{ display: 'flex', gap: '5px', marginTop: '5px' }}>
                      <input type="text" placeholder="Paste YouTube Link..." value={ytUrl} onChange={(e) => setYtUrl(e.target.value)} style={{ flex: 1, padding: '8px', background: '#0f172a', border: '1px solid #334155', color: '#fff', boxSizing: 'border-box' }} />
                      <button className="btn" onClick={scanYouTube} disabled={isYtScanning || !ytUrl} style={{ background: isYtScanning ? '#334155' : 'transparent', color: isYtScanning ? '#94a3b8' : '#eab308', border: '1px solid #eab308', fontWeight: 'bold' }}>
                        {isYtScanning ? "..." : "SCAN"}
                      </button>
                  </div>
              </div>

              <div style={{ marginBottom: '10px' }}>
                  <span style={{ color: '#94a3b8', fontSize: '12px' }}>OPTION B: KEYWORD SWEEP (TOP 3)</span>
                  <div style={{ display: 'flex', gap: '5px', marginTop: '5px' }}>
                      <input type="text" placeholder="Search (e.g., Dewald Brevis)" value={ytKeyword} onChange={(e) => setYtKeyword(e.target.value)} style={{ flex: 1, padding: '8px', background: '#0f172a', border: '1px solid #334155', color: '#fff', boxSizing: 'border-box' }} />
                      <button className="btn" onClick={sweepYouTube} disabled={isSweeping || !ytKeyword} style={{ background: isSweeping ? '#334155' : '#eab308', color: isSweeping ? '#94a3b8' : '#000', border: '1px solid #eab308', fontWeight: 'bold' }}>
                        {isSweeping ? "..." : "SWEEP"}
                      </button>
                  </div>
              </div>

              <div style={{ marginTop: 'auto', minHeight: '60px' }}>
                  {ytResult && (
                      <div style={{ padding: '8px', background: 'rgba(0,0,0,0.5)', borderLeft: `3px solid ${ytResult.includes('🚨') ? '#ef4444' : '#10b981'}`, fontSize: '11px', color: '#fff', whiteSpace: 'pre-wrap', lineHeight: '1.4' }}>
                          {ytResult}
                      </div>
                  )}
              </div>
            </div>
        </div>

        {/* --- BOTTOM ROW: Video Sync + Similarity (Left) | Telemetry (Right) --- */}
        <div style={{ display: 'flex', gap: '20px', alignItems: 'stretch' }}>

            {/* Left Area (Radar & Similarity Bar) */}
            <div style={{ flex: 2.2, display: 'flex', flexDirection: 'column', gap: '20px' }}>

                {/* The Video / Radar Zone */}
                <div className="card video-sync-zone" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', padding: '20px' }}>

                  <div className="player-container" style={{ flex: 1 }}>
  <h3 style={{ textAlign: 'center' }}>LIVE FEED INTERCEPT</h3>
  <video
      key={suspectSrc}
      ref={suspectPlayerRef}
      src={suspectSrc}
      muted
      crossOrigin="anonymous"
      onEnded={handleVideoEnd}
      style={{ width: '100%', borderRadius: '4px', border: '1px solid #334155' }}
  />
</div>

                  <div className="vector-visualizer" style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'center', width: '150px' }}>
                    <div className="hash-string" style={{ fontSize: '10px', color: '#64748b' }}>{currentHash || "AWAITING TENSOR"}</div>
                    <div style={{ width: '120px', height: '120px', border: `2px solid ${isLocked ? '#ef4444' : '#334155'}`, background: '#000', overflow: 'hidden' }}>
                        {neuralVision ? (
                            <img src={neuralVision} alt="Neural Tensor" style={{ width: '100%', height: '100%', opacity: 0.8, objectFit: 'cover' }} />
                        ) : (
                            <div style={{ color: '#334155', fontSize: '10px', marginTop: '50px', textAlign: 'center' }}>STANDBY</div>
                        )}
                    </div>
                    {isLocked ? (
                      <div className="locked-text" style={{ textAlign: 'center' }}>
                        <div style={{ color: '#ef4444', fontWeight: 'bold' }}>[ TARGET LOCKED ]</div>
                        <div style={{ fontSize: '16px', marginTop: '5px', color: '#fff' }}>{matchConfidence}</div>
                        <div style={{ fontSize: '12px', marginTop: '5px', color: '#10b981' }}>{targetFrame}</div>
                      </div>
                    ) : (
                      <div style={{ color: '#334155', textAlign: 'center' }}>
                         <div style={{ fontWeight: 'bold' }}>{isScanning ? "ALIGNING..." : "STANDBY"}</div>
                         <div style={{ fontSize: '11px', marginTop: '5px' }}>{targetFrame}</div>
                      </div>
                    )}
                  </div>

                  <div className="player-container" style={{ flex: 1 }}>
                    <h3 style={{ textAlign: 'center' }}>REFERENCE ASSET</h3>
                    <video ref={officialPlayerRef} muted style={{ width: '100%', borderRadius: '4px', border: '1px solid #334155' }}>
                      {isVaultLocked && (
                          <source src={`https://thecapybara-sportshield-engine.hf.space/static/official_source.mp4?t=${vaultTimestamp}`} type="video/mp4" />
                      )}
                    </video>
                  </div>

                </div>

                {/* The Live Tensor Similarity Bar */}
                <div className="card" style={{ padding: '15px' }}>
                    <h4 style={{ margin: '0 0 10px 0', color: '#60a5fa' }}>LIVE TENSOR SIMILARITY (INNER PRODUCT)</h4>
                    <div style={{ width: '100%', height: '20px', background: '#000', borderRadius: '10px', overflow: 'hidden', border: '1px solid #334155' }}>
                        <div style={{
                            height: '100%',
                            width: `${liveConfidence}%`,
                            background: parseFloat(liveConfidence) >= parseFloat(liveThreshold) ? '#ef4444' : '#10b981',
                            transition: 'width 0.1s linear, background 0.3s',
                            boxShadow: `0 0 10px ${parseFloat(liveConfidence) >= parseFloat(liveThreshold) ? '#ef4444' : '#10b981'}`
                        }}></div>
                    </div>
                    <div style={{ textAlign: 'right', marginTop: '5px', fontSize: '12px', color: parseFloat(liveConfidence) >= parseFloat(liveThreshold) ? '#ef4444' : '#10b981' }}>
                        CURRENT SCORE: {liveConfidence}% | DYNAMIC THRESHOLD: {liveThreshold}%
                    </div>
                </div>
            </div>

            {/* Right Area (Telemetry Box) */}
            <div className="terminal-panel card" style={{ flex: 1, margin: 0, display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ color: '#60a5fa', margin: '0 0 15px 0', borderBottom: '1px solid #334155', paddingBottom: '5px' }}>
                NEURAL TELEMETRY
              </h3>
              {/* This inner div ensures the scrollbar stays inside the panel while the border matches the left column */}
              <div style={{ flex: 1, overflowY: 'auto', maxHeight: '450px' }}>
                  {telemetryLogs.map((log, i) => (
                    <div key={i} className={`log-entry log-${log.type}`} style={{ fontSize: '12px', marginBottom: '8px' }}>
                      <span style={{ color: '#475569', marginRight: '8px' }}>[{log.time}]</span>
                      {log.msg}
                    </div>
                  ))}
                  <div ref={logsEndRef} />
              </div>
            </div>

        </div>

        <canvas ref={canvasRef} width="224" height="224" style={{ display: 'none' }} />

      </div>
    </div>
  );
}

export default App;
