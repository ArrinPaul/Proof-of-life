"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState, useMemo } from "react";

interface FaceIDScannerProps {
  isScanning: boolean;
  progress: number;
  status: "idle" | "scanning" | "success" | "error";
  scores?: {
    liveness: number;
    emotion: number;
    deepfake: number;
  };
  currentChallenge?: string;
  completedChallenges?: number;
  totalChallenges?: number;
}

const statusColor = (s: string) =>
  s === "success" ? "#00ff88" : s === "error" ? "#ff3366" : "#00f0ff";

/* ── deterministic face mesh ── */
function buildMesh(): [number, number][] {
  const p: [number, number][] = [];
  for (let i = 0; i < 36; i++) {
    const a = (i / 36) * Math.PI * 2;
    p.push([0.5 + Math.cos(a) * (0.36 + Math.sin(a * 3) * 0.012), 0.47 + Math.sin(a) * (0.44 + Math.cos(a * 2) * 0.012)]);
  }
  // eyes
  for (const cx of [0.39, 0.61]) {
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      p.push([cx + Math.cos(a) * 0.05, 0.37 + Math.sin(a) * 0.025]);
    }
    p.push([cx, 0.37]); // iris
  }
  // nose
  p.push([0.50, 0.42], [0.48, 0.50], [0.50, 0.52], [0.52, 0.50], [0.46, 0.53], [0.54, 0.53]);
  // mouth
  p.push([0.40, 0.62], [0.44, 0.59], [0.48, 0.58], [0.50, 0.58], [0.52, 0.58], [0.56, 0.59], [0.60, 0.62]);
  p.push([0.56, 0.65], [0.52, 0.66], [0.50, 0.66], [0.48, 0.66], [0.44, 0.65]);
  // brows
  p.push([0.30, 0.31], [0.34, 0.28], [0.38, 0.27], [0.42, 0.28], [0.46, 0.30]);
  p.push([0.54, 0.30], [0.58, 0.28], [0.62, 0.27], [0.66, 0.28], [0.70, 0.31]);
  // forehead, chin, jaw
  p.push([0.35, 0.20], [0.42, 0.17], [0.50, 0.15], [0.58, 0.17], [0.65, 0.20]);
  p.push([0.45, 0.78], [0.50, 0.82], [0.55, 0.78], [0.30, 0.55], [0.25, 0.47], [0.70, 0.55], [0.75, 0.47]);
  // interior fill
  for (let yi = 0; yi < 8; yi++)
    for (let xi = 0; xi < 7; xi++) {
      const x = 0.30 + xi * 0.06, y = 0.22 + yi * 0.08;
      if ((x - 0.5) ** 2 / 0.15 + (y - 0.47) ** 2 / 0.24 < 1)
        p.push([x + ((xi * 7 + yi * 3) % 5 - 2) * 0.004, y + ((xi * 3 + yi * 7) % 5 - 2) * 0.004]);
    }
  return p;
}

function buildEdges(pts: [number, number][], maxD = 0.095) {
  const e: [number, number, number, number][] = [];
  for (let i = 0; i < pts.length; i++)
    for (let j = i + 1; j < pts.length; j++) {
      const d = Math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]);
      if (d < maxD) e.push([pts[i][0], pts[i][1], pts[j][0], pts[j][1]]);
    }
  return e;
}

const RING_CHARS = "0123456789ABCDEF.:";
function makeRing(n: number, rx: number, ry: number, cx: number, cy: number) {
  return Array.from({ length: n }, (_, i) => {
    const a = (i / n) * Math.PI * 2 - Math.PI / 2;
    return { x: cx + Math.cos(a) * rx, y: cy + Math.sin(a) * ry, ch: RING_CHARS[i % RING_CHARS.length], rot: (a * 180) / Math.PI + 90 };
  });
}

export default function FaceIDScanner({
  isScanning, progress, status, scores, currentChallenge,
  completedChallenges = 0, totalChallenges = 8,
}: FaceIDScannerProps) {
  const [active, setActive] = useState<Set<number>>(new Set());
  const [tick, setTick] = useState(0);
  const pts = useMemo(buildMesh, []);
  const edges = useMemo(() => buildEdges(pts), [pts]);
  const ring = useMemo(() => makeRing(48, 152, 195, 160, 200), []);

  useEffect(() => {
    if (!isScanning) { setActive(new Set()); setTick(0); return; }
    const iv = setInterval(() => {
      setActive(prev => {
        const s = new Set(prev);
        for (let k = 0; k < 5; k++) s.add(Math.floor(Math.random() * pts.length));
        if (s.size > 28) { const a = Array.from(s); for (let k = 0; k < 4; k++) s.delete(a[Math.floor(Math.random() * a.length)]); }
        return s;
      });
      setTick(t => t + 1);
    }, 120);
    return () => clearInterval(iv);
  }, [isScanning, pts.length]);

  const c = statusColor(status);
  const W = 320, H = 400;

  return (
    <div className="relative w-full h-full flex items-center justify-center select-none overflow-hidden">
      {/* bg */}
      <div className="absolute inset-0 bg-void-50/90 backdrop-blur-xl border border-white/[0.03]" style={{ borderRadius: '2px' }}>
        <div className="absolute inset-0 bg-grid opacity-20" />
      </div>

      {/* ambient glow */}
      <motion.div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[440px] h-[440px] rounded-full pointer-events-none"
        style={{ background: `radial-gradient(circle, ${c}0a 0%, transparent 65%)` }}
        animate={isScanning ? { scale: [1, 1.18, 1], opacity: [0.25, 0.55, 0.25] } : { scale: 1, opacity: 0.08 }}
        transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }} />

      {/* SVG */}
      <motion.div className="relative z-10" initial={{ scale: 0.85, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.6 }}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="relative z-20">
          <defs>
            <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={`${c}00`} /><stop offset="40%" stopColor={`${c}18`} /><stop offset="100%" stopColor={`${c}00`} />
            </linearGradient>
            <filter id="glow"><feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          </defs>

          {/* outer data-ring */}
          <motion.g style={{ transformOrigin: `${W / 2}px ${H / 2}px` }}
            animate={isScanning ? { rotate: 360 } : { rotate: 0 }}
            transition={{ duration: 40, repeat: Infinity, ease: "linear" }}>
            <ellipse cx={W / 2} cy={H * 0.5} rx={W * 0.47} ry={H * 0.49} fill="none" stroke={c} strokeWidth="0.4" strokeDasharray="3 8" opacity={isScanning ? 0.2 : 0.06} />
            {ring.map((ch, i) => (
              <text key={i} x={ch.x} y={ch.y} fill={c} fontSize="6" fontFamily="JetBrains Mono"
                textAnchor="middle" dominantBaseline="middle"
                opacity={isScanning ? ((i + tick) % 6 < 3 ? 0.35 : 0.1) : 0.04}
                transform={`rotate(${ch.rot},${ch.x},${ch.y})`}>{ch.ch}</text>
            ))}
          </motion.g>

          {/* counter-rotating ring */}
          <motion.g style={{ transformOrigin: `${W / 2}px ${H / 2}px` }}
            animate={isScanning ? { rotate: -360 } : { rotate: 0 }}
            transition={{ duration: 30, repeat: Infinity, ease: "linear" }}>
            <ellipse cx={W / 2} cy={H * 0.5} rx={W * 0.43} ry={H * 0.45} fill="none" stroke={c} strokeWidth="0.3" strokeDasharray="2 14" opacity={isScanning ? 0.15 : 0.04} />
          </motion.g>

          {/* mesh edges */}
          {edges.map((e, i) => (
            <line key={i} x1={e[0] * W} y1={e[1] * H} x2={e[2] * W} y2={e[3] * H}
              stroke={c} strokeWidth="0.5"
              opacity={isScanning ? 0.04 + Math.abs(Math.sin(tick * 0.08 + i * 0.04)) * 0.12 : 0.02} />
          ))}

          {/* face oval */}
          <motion.ellipse cx={W / 2} cy={H * 0.47} rx={W * 0.37} ry={H * 0.42} fill="none" stroke={c} strokeWidth="1.4"
            strokeDasharray="5 4"
            animate={{ opacity: isScanning ? 0.45 : 0.12, strokeDashoffset: isScanning ? [0, -36] : 0 }}
            transition={{ strokeDashoffset: { duration: 5, repeat: Infinity, ease: "linear" }, opacity: { duration: 0.4 } }} />

          {/* mesh nodes */}
          {pts.map((p, i) => {
            const on = active.has(i);
            return (
              <circle key={i} cx={p[0] * W} cy={p[1] * H}
                r={on ? 2.5 : 1} fill={on ? c : `${c}50`}
                opacity={isScanning ? (on ? 0.9 : 0.12) : 0.04}
                style={on ? { filter: `drop-shadow(0 0 4px ${c})` } : undefined} />
            );
          })}

          {/* scan beam */}
          {isScanning && (
            <motion.g>
              <motion.line x1={0} y1={0} x2={W} y2={0} stroke={c} strokeWidth="1.5" filter="url(#glow)"
                animate={{ y1: [0, H, 0], y2: [0, H, 0] }}
                transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }} />
              <motion.rect x={0} y={0} width={W} height={36} fill="url(#sg)"
                animate={{ y: [-36, H, -36] }}
                transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }} />
            </motion.g>
          )}

          {/* HUD text */}
          {isScanning && (
            <g>
              <text x={8} y={18} fill={c} fontSize="7" fontFamily="JetBrains Mono" opacity="0.35">SENTINEL / MESH.4K</text>
              <text x={8} y={30} fill={c} fontSize="7" fontFamily="JetBrains Mono" opacity={tick % 6 < 3 ? 0.5 : 0.2}>▸ TRACK {active.size} NODES</text>
              <text x={W - 8} y={18} fill={c} fontSize="7" fontFamily="JetBrains Mono" textAnchor="end" opacity="0.3">FPS 30 / {Math.round(progress)}%</text>
              <text x={W - 8} y={30} fill={c} fontSize="7" fontFamily="JetBrains Mono" textAnchor="end" opacity={tick % 8 < 4 ? 0.4 : 0.15}>DEPTH OK</text>
              <text x={W / 2} y={H - 12} fill={c} fontSize="7" fontFamily="JetBrains Mono" textAnchor="middle" opacity="0.2">
                {`${String((tick * 17) % 256).padStart(2, '0')}:${String((tick * 31) % 256).padStart(2, '0')}:${String((tick * 53) % 256).padStart(2, '0')}`} — BIOMETRIC
              </text>
            </g>
          )}
        </svg>

        {/* corner brackets */}
        <div className="absolute inset-0 pointer-events-none">
          {[
            { p: 'top-0 left-0', b: 'border-t-2 border-l-2' },
            { p: 'top-0 right-0', b: 'border-t-2 border-r-2' },
            { p: 'bottom-0 left-0', b: 'border-b-2 border-l-2' },
            { p: 'bottom-0 right-0', b: 'border-b-2 border-r-2' },
          ].map(({ p, b }, i) => (
            <motion.div key={i} className={`absolute ${p} w-8 h-8 ${b}`}
              style={{ borderColor: c, filter: `drop-shadow(0 0 4px ${c}60)` }}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: isScanning ? 1 : 0.25, scale: 1 }}
              transition={{ delay: i * 0.05, duration: 0.3 }} />
          ))}
        </div>
      </motion.div>

      {/* challenge progress pips */}
      {isScanning && totalChallenges > 0 && (
        <motion.div className="absolute bottom-16 left-1/2 -translate-x-1/2 flex items-center gap-1 z-30"
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          {Array.from({ length: totalChallenges }).map((_, i) => (
            <motion.div key={i} className="h-[3px] rounded-full"
              style={{
                width: i < completedChallenges ? 28 : 18,
                backgroundColor: i < completedChallenges ? c : `${c}18`,
                boxShadow: i < completedChallenges ? `0 0 8px ${c}90` : 'none',
              }}
              animate={i === completedChallenges ? { opacity: [0.25, 1, 0.25] } : {}}
              transition={{ duration: 0.9, repeat: Infinity }} />
          ))}
        </motion.div>
      )}

      {/* bottom label */}
      {isScanning && (
        <motion.div className="absolute bottom-7 left-1/2 -translate-x-1/2 z-30"
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <motion.p className="text-center text-[10px] font-mono tracking-[0.25em] uppercase"
            style={{ color: c }} animate={{ opacity: [0.35, 0.75, 0.35] }}
            transition={{ duration: 2.8, repeat: Infinity }}>
            {completedChallenges}/{totalChallenges} — Biometric Analysis
          </motion.p>
        </motion.div>
      )}

      {/* challenge instruction */}
      <AnimatePresence mode="wait">
        {currentChallenge && isScanning && (
          <motion.div className="absolute top-5 left-1/2 -translate-x-1/2 z-30 max-w-[92%]"
            key={currentChallenge}
            initial={{ opacity: 0, y: -12, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }} transition={{ duration: 0.22 }}>
            <div className="bg-void-100/90 backdrop-blur-md border border-neon-cyan/25 px-5 py-3 shadow-glow-cyan" style={{ borderRadius: '2px' }}>
              <div className="flex items-center gap-3">
                <motion.div className="w-2 h-2 rounded-full bg-neon-cyan shrink-0"
                  animate={{ scale: [1, 1.5, 1], opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1, repeat: Infinity }}
                  style={{ boxShadow: '0 0 8px #00f0ff' }} />
                <p className="text-ink-100 font-mono text-sm tracking-wide whitespace-nowrap">{currentChallenge}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* success overlay */}
      <AnimatePresence>
        {status === "success" && (
          <motion.div className="absolute inset-0 flex items-center justify-center z-40"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {[0, 0.25, 0.5].map((d, i) => (
              <motion.div key={i} className="absolute w-28 h-28 rounded-full border" style={{ borderColor: '#00ff8850' }}
                initial={{ scale: 0.4, opacity: 0 }} animate={{ scale: [0.4, 2.8], opacity: [0.7, 0] }}
                transition={{ duration: 1.4, delay: d, repeat: Infinity }} />
            ))}
            <motion.div className="w-20 h-20 rounded-full bg-neon-green/10 backdrop-blur-md flex items-center justify-center border border-neon-green/40"
              initial={{ scale: 0 }} animate={{ scale: [0, 1.15, 1] }} transition={{ duration: 0.45 }}
              style={{ boxShadow: '0 0 50px rgba(0,255,136,0.35)' }}>
              <svg className="w-10 h-10 text-neon-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <motion.path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7"
                  initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.35, delay: 0.2 }} />
              </svg>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* error overlay */}
      <AnimatePresence>
        {status === "error" && (
          <motion.div className="absolute inset-0 flex items-center justify-center z-40"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <motion.div className="w-20 h-20 rounded-full bg-neon-red/10 backdrop-blur-md flex items-center justify-center border border-neon-red/40"
              initial={{ scale: 0 }} animate={{ scale: [0, 1.15, 1] }} transition={{ duration: 0.45 }}
              style={{ boxShadow: '0 0 50px rgba(255,51,102,0.35)' }}>
              <svg className="w-10 h-10 text-neon-red" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <motion.path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12"
                  initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.35, delay: 0.15 }} />
              </svg>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* HUD score bars */}
      {scores && isScanning && (
        <motion.div className="absolute top-5 right-3 z-30 space-y-1.5"
          initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
          {[
            { label: 'LIV', v: scores.liveness, hex: '#00ff88' },
            { label: 'EMO', v: scores.emotion, hex: '#a855f7' },
            { label: 'DPF', v: scores.deepfake, hex: '#00f0ff' },
          ].map(s => (
            <div key={s.label} className="bg-void-100/70 backdrop-blur-md border border-white/[0.05] px-2.5 py-1.5 min-w-[108px]" style={{ borderRadius: '1px' }}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-[8px] font-mono tracking-[0.2em] uppercase" style={{ color: `${s.hex}80` }}>{s.label}</span>
                <span className="text-[11px] font-mono font-bold" style={{ color: s.hex }}>{Math.round(s.v * 100)}%</span>
              </div>
              <div className="h-[2px] bg-white/[0.04] overflow-hidden" style={{ borderRadius: '1px' }}>
                <motion.div className="h-full" style={{ backgroundColor: s.hex, boxShadow: `0 0 6px ${s.hex}60` }}
                  initial={{ width: "0%" }} animate={{ width: `${Math.min(s.v * 100, 100)}%` }}
                  transition={{ duration: 0.35 }} />
              </div>
            </div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
