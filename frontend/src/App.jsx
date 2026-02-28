import { useState, useEffect, useRef, useCallback } from "react";
import {
  StreamVideo,
  StreamVideoClient,
  StreamCall,
  useCallStateHooks,
  ParticipantView,
  CallingState,
} from "@stream-io/video-react-sdk";
import "@stream-io/video-react-sdk/dist/css/styles.css";
import "./App.css";

// ─── Config ──────────────────────────────────────────────────────────────────
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ─── Exercise Library ─────────────────────────────────────────────────────────
const EXERCISES = [
  { id: "KNEE_BEND",         name: "Knee Bend",          target: "Post-Knee Surgery",   reps: 10, sets: 3, icon: "🦵" },
  { id: "SHOULDER_ROTATION", name: "Shoulder Rotation",  target: "Shoulder Recovery",   reps: 15, sets: 3, icon: "💪" },
  { id: "HIP_ABDUCTION",     name: "Hip Abduction",      target: "Hip Replacement",     reps: 10, sets: 3, icon: "🏃" },
  { id: "ANKLE_PUMP",        name: "Ankle Pump",         target: "DVT Prevention",      reps: 20, sets: 4, icon: "🦶" },
  { id: "QUAD_SET",          name: "Quad Set",           target: "Quadriceps Strength", reps: 12, sets: 3, icon: "🧘" },
  { id: "SLR",               name: "Straight Leg Raise", target: "Hip Flexor Rehab",    reps: 10, sets: 3, icon: "⬆️"  },
];

// ─── Hex Grid Background Component ───────────────────────────────────────────
function HexGrid() {
  return (
    <div className="hex-grid" aria-hidden="true">
      {Array.from({ length: 80 }).map((_, i) => (
        <div key={i} className="hex-cell" style={{ animationDelay: `${(i * 0.07) % 5}s` }} />
      ))}
    </div>
  );
}

// ─── Circular Audio Visualizer ────────────────────────────────────────────────
function AudioRing({ isActive, isSpeaking }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const analyserRef = useRef(null);
  const dataRef = useRef(null);

  useEffect(() => {
    if (!isActive) return;
    let stream;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const ctx = new AudioContext();
        const src = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        src.connect(analyser);
        analyserRef.current = analyser;
        dataRef.current = new Uint8Array(analyser.frequencyBinCount);
      } catch (_) {}
    })();
    return () => { stream?.getTracks().forEach(t => t.stop()); };
  }, [isActive]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    const cx = W / 2, cy = H / 2;
    const baseR = 80, barMax = 60;
    const BARS = 128;

    const draw = () => {
      animRef.current = requestAnimationFrame(draw);
      ctx.clearRect(0, 0, W, H);

      let data = new Array(BARS).fill(0);
      if (analyserRef.current && dataRef.current) {
        analyserRef.current.getByteFrequencyData(dataRef.current);
        for (let i = 0; i < BARS; i++) {
          data[i] = dataRef.current[Math.floor(i * dataRef.current.length / BARS)] / 255;
        }
      } else if (isSpeaking) {
        for (let i = 0; i < BARS; i++) {
          data[i] = 0.1 + Math.random() * 0.5 * Math.sin(Date.now() / 200 + i * 0.3);
        }
      }

      // outer glow ring
      const grd = ctx.createRadialGradient(cx, cy, baseR - 10, cx, cy, baseR + 20);
      grd.addColorStop(0, "rgba(0,240,255,0.05)");
      grd.addColorStop(1, "rgba(0,240,255,0)");
      ctx.beginPath();
      ctx.arc(cx, cy, baseR + 10, 0, Math.PI * 2);
      ctx.fillStyle = grd;
      ctx.fill();

      for (let i = 0; i < BARS; i++) {
        const angle = (i / BARS) * Math.PI * 2 - Math.PI / 2;
        const h = data[i] * barMax;
        const x1 = cx + Math.cos(angle) * baseR;
        const y1 = cy + Math.sin(angle) * baseR;
        const x2 = cx + Math.cos(angle) * (baseR + Math.max(3, h));
        const y2 = cy + Math.sin(angle) * (baseR + Math.max(3, h));

        const alpha = isActive ? 0.6 + data[i] * 0.4 : 0.15;
        const hue = isSpeaking ? 180 + data[i] * 60 : 180;
        ctx.beginPath();
        ctx.strokeStyle = `hsla(${hue}, 100%, 65%, ${alpha})`;
        ctx.lineWidth = 2.5;
        ctx.lineCap = "round";
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // center circle
      ctx.beginPath();
      ctx.arc(cx, cy, baseR - 8, 0, Math.PI * 2);
      ctx.strokeStyle = isSpeaking ? "rgba(0,240,255,0.8)" : "rgba(0,240,255,0.2)";
      ctx.lineWidth = 1;
      ctx.stroke();
    };
    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, [isActive, isSpeaking]);

  return (
    <canvas
      ref={canvasRef}
      width={300}
      height={300}
      className="audio-ring"
    />
  );
}

// ─── HUD Stats Panel ──────────────────────────────────────────────────────────
function StatsPanel({ stats }) {
  return (
    <div className="stats-panel">
      <div className="stats-header">
        <span className="scan-line" />
        BIOMETRICS
      </div>
      <div className="stats-grid">
        {[
          { label: "FORM SCORE", value: stats.formScore + "%", color: stats.formScore > 75 ? "#00f0ff" : "#ff6b35" },
          { label: "CURRENT REP", value: `${stats.currentRep}/${stats.totalReps}`, color: "#00f0ff" },
          { label: "SETS DONE", value: `${stats.setsCompleted}/${stats.totalSets}`, color: "#00f0ff" },
          { label: "SESSION", value: stats.sessionTime, color: "#7fff7f" },
          { label: "JOINT ANGLE", value: stats.jointAngle + "°", color: "#ffdd57" },
          { label: "STATUS", value: stats.status, color: stats.status === "GOOD" ? "#7fff7f" : "#ff6b35" },
        ].map(s => (
          <div key={s.label} className="stat-item">
            <span className="stat-label">{s.label}</span>
            <span className="stat-value" style={{ color: s.color }}>{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Exercise Selector ────────────────────────────────────────────────────────
function ExerciseSelector({ selected, onSelect }) {
  return (
    <div className="exercise-selector">
      <div className="panel-header">SELECT PROTOCOL</div>
      <div className="exercise-grid">
        {EXERCISES.map(ex => (
          <button
            key={ex.id}
            className={`exercise-card ${selected?.id === ex.id ? "active" : ""}`}
            onClick={() => onSelect(ex)}
          >
            <span className="ex-icon">{ex.icon}</span>
            <span className="ex-name">{ex.name}</span>
            <span className="ex-target">{ex.target}</span>
            <span className="ex-meta">{ex.sets}×{ex.reps}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Transcript Feed ──────────────────────────────────────────────────────────
function TranscriptFeed({ messages }) {
  const bottomRef = useRef(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  return (
    <div className="transcript">
      <div className="panel-header">COMMS LOG</div>
      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <span className="msg-role">{m.role === "agent" ? "REHAB AI" : "YOU"}</span>
            <span className="msg-text">{m.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ─── Video Call Component (inner — uses Stream hooks) ─────────────────────────
function CallView({ callId, onMessage }) {
  const { useCallCallingState, useRemoteParticipants, useLocalParticipant } = useCallStateHooks();
  const callingState = useCallCallingState();
  const remoteParticipants = useRemoteParticipants();
  const localParticipant = useLocalParticipant();
  const audioRefs = useRef({});

  const isConnected = callingState === CallingState.JOINED;
  const agentParticipant = remoteParticipants.find(p => p.userId?.includes("agent"));

  // ── Auto-play agent audio tracks ──────────────────────────────────────────
  useEffect(() => {
    remoteParticipants.forEach(participant => {
      const audioStream = participant.audioStream;
      if (!audioStream) return;
      const key = participant.sessionId;
      if (audioRefs.current[key]) return; // already 
      const audio = new Audio();
      audio.srcObject = audioStream;
      audio.autoplay = true;
      audio.play().catch(e => console.warn("Audio play failed:", e));
      audioRefs.current[key] = audio;
      console.log("audio for:", participant.userId);
    });
  }, [remoteParticipants]);

  return (
    <div className="call-view">
      {/* Patient video (local) */}
      <div className="video-main">
        {localParticipant && (
          <ParticipantView
            participant={localParticipant}
            className="video-patient"
          />
        )}
        {/* Skeleton overlay label */}
        <div className="video-overlay-label">
          <span className="blink-dot" />
          POSE TRACKING ACTIVE
        </div>
        {/* Corner brackets */}
        <div className="corner tl" /><div className="corner tr" />
        <div className="corner bl" /><div className="corner br" />
      </div>

      {/* Connection status */}
      <div className={`conn-badge ${isConnected ? "connected" : "connecting"}`}>
        {isConnected ? "● LIVE" : "◌ CONNECTING..."}
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [phase, setPhase] = useState("idle"); // idle | setup | session | summary
  const [selectedExercise, setSelectedExercise] = useState(null);
  const [client, setClient] = useState(null);
  const [call, setCall] = useState(null);
  const [messages, setMessages] = useState([
    { role: "agent", text: "REHAB AI online. All systems nominal. Select your rehabilitation protocol to begin." }
  ]);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [stats, setStats] = useState({
    formScore: 0, currentRep: 0, totalReps: 0,
    setsCompleted: 0, totalSets: 0, jointAngle: 0,
    sessionTime: "00:00", status: "IDLE"
  });
  const timerRef = useRef(null);
  const secondsRef = useRef(0);

  // ── Session timer ──
  useEffect(() => {
    if (phase === "session") {
      timerRef.current = setInterval(() => {
        secondsRef.current++;
        const m = String(Math.floor(secondsRef.current / 60)).padStart(2, "0");
        const s = String(secondsRef.current % 60).padStart(2, "0");
        setStats(prev => ({ ...prev, sessionTime: `${m}:${s}` }));
      }, 1000);
    }
    return () => clearInterval(timerRef.current);
  }, [phase]);

  // ── Demo stats simulation (replace with real pose data from agent events) ──
  useEffect(() => {
    if (phase !== "session" || !selectedExercise) return;
    setStats(prev => ({
      ...prev,
      totalReps: selectedExercise.reps,
      totalSets: selectedExercise.sets,
      status: "ACTIVE",
    }));
    // const sim = setInterval(() => {
    //   setStats(prev => {
    //     const newAngle = Math.floor(60 + Math.random() * 35);
    //     const newScore = Math.floor(72 + Math.random() * 23);
    //     const newRep = Math.min(prev.currentRep + (Math.random() > 0.85 ? 1 : 0), selectedExercise.reps);
    //     const newSets = newRep >= selectedExercise.reps ? Math.min(prev.setsCompleted + 1, selectedExercise.sets) : prev.setsCompleted;
    //     return {
    //       ...prev,
    //       formScore: newScore,
    //       jointAngle: newAngle,
    //       currentRep: newRep >= selectedExercise.reps ? 0 : newRep,
    //       setsCompleted: newSets,
    //       status: newScore > 75 ? "GOOD" : "CORRECT",
    //     };
    //   });
    // }, 2000);
    // return () => clearInterval(sim);
  }, [phase, selectedExercise]);

  const startSession = async () => {
    if (!selectedExercise) return;
    setPhase("session");

    // ── Initialize Stream client ──
    // In production, fetch token from your backend
    try {
      const res = await fetch(`${API_URL}/token?user_id=patient-001`);
      const { token, api_key } = await res.json();

      const streamClient = new StreamVideoClient({
        apiKey: api_key,
        user: { id: "patient-001", name: "Patient" },
        token,
      });

      const callId = `rehab-${Date.now()}`;
      const streamCall = streamClient.call("default", callId, {
        iceServers: [
          { urls: "stun:stun.l.google.com:19302" },
          { urls: "stun:stun1.l.google.com:19302" },
          { urls: "stun:global.stun.twilio.com:3478" },
        ]
      });
      await streamCall.join({ create: true });

      // Notify backend to start agent
      await fetch(`${API_URL}/start-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ call_id: callId, exercise: selectedExercise.id }),
      });

      setClient(streamClient);
      setCall(streamCall);
      setMessages(prev => [...prev, {
        role: "agent",
        text: `Initiating ${selectedExercise.name} protocol. ${selectedExercise.sets} sets of ${selectedExercise.reps} reps. Assume starting position when ready.`
      }]);
      setIsAgentSpeaking(true);
      setTimeout(() => setIsAgentSpeaking(false), 4000);

    } catch (err) {
      // Demo mode — no backend
      console.warn("Running in demo mode:", err.message);
      setMessages(prev => [...prev, {
        role: "agent",
        text: `Demo mode active. ${selectedExercise.name} protocol loaded. ${selectedExercise.sets} sets of ${selectedExercise.reps} reps.`
      }]);
    }
  };

  const endSession = () => {
    call?.leave().catch(console.error);
    client?.disconnectUser().catch(console.error);
    clearInterval(timerRef.current);
    setPhase("summary");
    setMessages(prev => [...prev, {
      role: "agent",
      text: `Session complete. ${stats.setsCompleted} sets completed. Average form score: ${stats.formScore}%. Good work. Rest and hydrate.`
    }]);
  };

  return (
    <div className="app">
      <HexGrid />

      {/* ── Top Bar ── */}
      <header className="topbar">
        <div className="logo-group">
          <div className="logo-icon">
            <svg viewBox="0 0 40 40" fill="none">
              <circle cx="20" cy="20" r="18" stroke="#00f0ff" strokeWidth="1.5" />
              <path d="M20 8 L28 32 L20 26 L12 32 Z" fill="#00f0ff" opacity="0.8" />
              <circle cx="20" cy="20" r="3" fill="#00f0ff" />
            </svg>
          </div>
          <div>
            <div className="logo-text">REHAB<span>AI</span></div>
            <div className="logo-sub">PHYSICAL THERAPY SYSTEM v1.0</div>
          </div>
        </div>
        <div className="topbar-center">
          {phase === "session" && (
            <div className="session-badge">
              <span className="pulse-dot" />
              SESSION ACTIVE — {selectedExercise?.name?.toUpperCase()}
            </div>
          )}
        </div>
        <div className="topbar-right">
          <div className="system-status">
            <span className="status-dot active" />SYS NOMINAL
          </div>
          <div className="time-display" id="clock">
            {new Date().toLocaleTimeString("en-US", { hour12: false })}
          </div>
        </div>
      </header>

      {/* ── Main Layout ── */}
      <main className="main-layout">

        {/* LEFT PANEL */}
        <aside className="left-panel">
          {phase === "idle" || phase === "setup" ? (
            <ExerciseSelector selected={selectedExercise} onSelect={setSelectedExercise} />
          ) : (
            <StatsPanel stats={stats} />
          )}

          {(phase === "idle" || phase === "setup") && (
            <button
              className={`start-btn ${selectedExercise ? "ready" : ""}`}
              onClick={startSession}
              disabled={!selectedExercise}
            >
              {selectedExercise ? `INITIATE ${selectedExercise.name.toUpperCase()}` : "SELECT EXERCISE TO BEGIN"}
            </button>
          )}
          {phase === "session" && (
            <button className="end-btn" onClick={endSession}>
              END SESSION
            </button>
          )}
          {phase === "summary" && (
            <button className="start-btn ready" onClick={() => { setPhase("idle"); secondsRef.current = 0; setStats(s => ({...s, sessionTime: "00:00", currentRep: 0, setsCompleted: 0})); }}>
              NEW SESSION
            </button>
          )}
        </aside>

        {/* CENTER — Video + Visualizer */}
        <section className="center-section">
          <div className="video-container">
            {phase === "session" && client && call ? (
              <StreamVideo client={client}>
                <StreamCall call={call}>
                  <CallView callId={call.id} onMessage={m => setMessages(prev => [...prev, m])} />
                </StreamCall>
              </StreamVideo>
            ) : (
              <div className="video-placeholder">
                <div className="placeholder-grid" />
                <div className="placeholder-text">
                  {phase === "idle" && "SELECT EXERCISE AND INITIATE SESSION"}
                  {phase === "summary" && "SESSION TERMINATED — DATA ARCHIVED"}
                </div>
                {/* Corner brackets */}
                <div className="corner tl" /><div className="corner tr" />
                <div className="corner bl" /><div className="corner br" />
              </div>
            )}
          </div>

          {/* Audio Visualizer Ring */}
          <div className="visualizer-section">
            <AudioRing isActive={phase === "session"} isSpeaking={isAgentSpeaking} />
            <div className="agent-status">
              <div className="agent-name">REHAB AI</div>
              <div className={`agent-state ${isAgentSpeaking ? "speaking" : phase === "session" ? "listening" : "idle"}`}>
                {isAgentSpeaking ? "ANALYZING" : phase === "session" ? "MONITORING" : "STANDBY"}
              </div>
            </div>
          </div>
        </section>

        {/* RIGHT PANEL */}
        <aside className="right-panel">
          <TranscriptFeed messages={messages} />
          {phase === "session" && (
            <div className="quick-feedback">
              <div className="panel-header">QUICK REPORT</div>
              {[
                { label: "Form Quality", bar: stats.formScore },
                { label: "Range of Motion", bar: Math.round(stats.jointAngle / 1.35) },
                { label: "Consistency", bar: 78 },
              ].map(item => (
                <div key={item.label} className="feedback-bar">
                  <span className="fb-label">{item.label}</span>
                  <div className="fb-track">
                    <div className="fb-fill" style={{ width: item.bar + "%" }} />
                  </div>
                  <span className="fb-val">{item.bar}%</span>
                </div>
              ))}
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}