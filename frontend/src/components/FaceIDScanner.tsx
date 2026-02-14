"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

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
}

export default function FaceIDScanner({ isScanning, progress, status, scores, currentChallenge }: FaceIDScannerProps) {
  const [scanLines, setScanLines] = useState<number[]>([]);

  useEffect(() => {
    if (isScanning) {
      const interval = setInterval(() => {
        setScanLines((prev) => {
          const newLines = [...prev, Math.random()];
          return newLines.slice(-20); // Keep last 20 lines
        });
      }, 100);
      return () => clearInterval(interval);
    } else {
      setScanLines([]);
    }
  }, [isScanning]);

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      {/* Glassmorphism background */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl" />

      {/* Face outline */}
      <motion.div
        className="relative z-10"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        {/* Outer glow ring */}
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            width: "280px",
            height: "360px",
            left: "50%",
            top: "50%",
            transform: "translate(-50%, -50%)",
          }}
          animate={{
            boxShadow: isScanning
              ? [
                  "0 0 20px rgba(59, 130, 246, 0.3)",
                  "0 0 40px rgba(59, 130, 246, 0.6)",
                  "0 0 20px rgba(59, 130, 246, 0.3)",
                ]
              : "0 0 0px rgba(59, 130, 246, 0)",
          }}
          transition={{ duration: 2, repeat: Infinity }}
        />

        {/* Face mesh grid */}
        <svg
          width="280"
          height="360"
          viewBox="0 0 280 360"
          className="relative z-20"
        >
          {/* Vertical lines */}
          {[...Array(15)].map((_, i) => (
            <motion.line
              key={`v-${i}`}
              x1={i * 20}
              y1="0"
              x2={i * 20}
              y2="360"
              stroke={
                status === "success"
                  ? "#10b981"
                  : status === "error"
                  ? "#ef4444"
                  : "#3b82f6"
              }
              strokeWidth="1"
              opacity="0.3"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: isScanning ? 1 : 0 }}
              transition={{ duration: 0.5, delay: i * 0.05 }}
            />
          ))}

          {/* Horizontal lines */}
          {[...Array(19)].map((_, i) => (
            <motion.line
              key={`h-${i}`}
              x1="0"
              y1={i * 20}
              x2="280"
              y2={i * 20}
              stroke={
                status === "success"
                  ? "#10b981"
                  : status === "error"
                  ? "#ef4444"
                  : "#3b82f6"
              }
              strokeWidth="1"
              opacity="0.3"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: isScanning ? 1 : 0 }}
              transition={{ duration: 0.5, delay: i * 0.05 }}
            />
          ))}

          {/* Face outline */}
          <motion.ellipse
            cx="140"
            cy="180"
            rx="120"
            ry="160"
            fill="none"
            stroke={
              status === "success"
                ? "#10b981"
                : status === "error"
                ? "#ef4444"
                : "#3b82f6"
            }
            strokeWidth="2"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{
              pathLength: 1,
              opacity: isScanning ? 0.8 : 0.3,
            }}
            transition={{ duration: 1 }}
          />

          {/* Scanning line */}
          <AnimatePresence>
            {isScanning && (
              <motion.line
                x1="0"
                y1="0"
                x2="280"
                y2="0"
                stroke="#3b82f6"
                strokeWidth="3"
                initial={{ y: 0, opacity: 0 }}
                animate={{
                  y: [0, 360, 0],
                  opacity: [0, 1, 0],
                }}
                exit={{ opacity: 0 }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
                style={{ filter: "blur(2px)" }}
              />
            )}
          </AnimatePresence>

          {/* Landmark dots */}
          {isScanning &&
            scanLines.map((line, i) => (
              <motion.circle
                key={i}
                cx={Math.random() * 280}
                cy={Math.random() * 360}
                r="2"
                fill="#3b82f6"
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: [0, 1, 0], scale: [0, 1, 0] }}
                transition={{ duration: 1 }}
              />
            ))}
        </svg>

        {/* Corner brackets */}
        <div className="absolute inset-0 pointer-events-none">
          {/* Top-left */}
          <motion.div
            className="absolute top-0 left-0 w-12 h-12 border-t-2 border-l-2 border-blue-500"
            initial={{ opacity: 0, x: -10, y: -10 }}
            animate={{ opacity: 1, x: 0, y: 0 }}
            transition={{ delay: 0.2 }}
          />
          {/* Top-right */}
          <motion.div
            className="absolute top-0 right-0 w-12 h-12 border-t-2 border-r-2 border-blue-500"
            initial={{ opacity: 0, x: 10, y: -10 }}
            animate={{ opacity: 1, x: 0, y: 0 }}
            transition={{ delay: 0.3 }}
          />
          {/* Bottom-left */}
          <motion.div
            className="absolute bottom-0 left-0 w-12 h-12 border-b-2 border-l-2 border-blue-500"
            initial={{ opacity: 0, x: -10, y: 10 }}
            animate={{ opacity: 1, x: 0, y: 0 }}
            transition={{ delay: 0.4 }}
          />
          {/* Bottom-right */}
          <motion.div
            className="absolute bottom-0 right-0 w-12 h-12 border-b-2 border-r-2 border-blue-500"
            initial={{ opacity: 0, x: 10, y: 10 }}
            animate={{ opacity: 1, x: 0, y: 0 }}
            transition={{ delay: 0.5 }}
          />
        </div>
      </motion.div>

      {/* Status indicator */}
      <AnimatePresence>
        {status === "success" && (
          <motion.div
            className="absolute inset-0 flex items-center justify-center z-30"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
          >
            <motion.div
              className="w-24 h-24 rounded-full bg-green-500/20 backdrop-blur-sm flex items-center justify-center"
              animate={{
                scale: [1, 1.2, 1],
              }}
              transition={{ duration: 0.5 }}
            >
              <svg
                className="w-12 h-12 text-green-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <motion.path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={3}
                  d="M5 13l4 4L19 7"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.5 }}
                />
              </svg>
            </motion.div>
          </motion.div>
        )}

        {status === "error" && (
          <motion.div
            className="absolute inset-0 flex items-center justify-center z-30"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
          >
            <motion.div
              className="w-24 h-24 rounded-full bg-red-500/20 backdrop-blur-sm flex items-center justify-center"
              animate={{
                scale: [1, 1.2, 1],
              }}
              transition={{ duration: 0.5 }}
            >
              <svg
                className="w-12 h-12 text-red-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <motion.path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={3}
                  d="M6 18L18 6M6 6l12 12"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.5 }}
                />
              </svg>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Progress bar */}
      {isScanning && (
        <motion.div
          className="absolute bottom-8 left-1/2 transform -translate-x-1/2 w-64"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="h-1 bg-white/10 rounded-full overflow-hidden backdrop-blur-sm">
            <motion.div
              className="h-full bg-gradient-to-r from-blue-500 to-cyan-500"
              initial={{ width: "0%" }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <motion.p
            className="text-center text-sm text-white/70 mt-2"
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            Analyzing biometric data...
          </motion.p>
        </motion.div>
      )}

      {/* Challenge Display */}
      <AnimatePresence>
        {currentChallenge && isScanning && (
          <motion.div
            className="absolute top-8 left-1/2 transform -translate-x-1/2 z-30"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <div className="bg-blue-500/20 backdrop-blur-md border border-blue-400/30 rounded-2xl px-6 py-4 shadow-lg">
              <div className="flex items-center gap-3">
                <motion.div
                  className="w-3 h-3 rounded-full bg-blue-400"
                  animate={{
                    scale: [1, 1.3, 1],
                    opacity: [0.5, 1, 0.5],
                  }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
                <p className="text-white font-medium text-lg">{currentChallenge}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Scores Display */}
      {scores && isScanning && (
        <motion.div
          className="absolute top-8 right-8 z-30 space-y-3"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Liveness Score */}
          <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl px-4 py-3 min-w-[180px]">
            <div className="flex justify-between items-center mb-2">
              <span className="text-white/80 text-sm font-medium">Liveness</span>
              <span className="text-white font-bold">{Math.round(scores.liveness * 100)}%</span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-green-400 to-green-500"
                initial={{ width: "0%" }}
                animate={{ width: `${scores.liveness * 100}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>

          {/* Emotion Score */}
          <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl px-4 py-3 min-w-[180px]">
            <div className="flex justify-between items-center mb-2">
              <span className="text-white/80 text-sm font-medium">Emotion</span>
              <span className="text-white font-bold">{Math.round(scores.emotion * 100)}%</span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-blue-400 to-blue-500"
                initial={{ width: "0%" }}
                animate={{ width: `${scores.emotion * 100}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>

          {/* Deepfake Score */}
          <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl px-4 py-3 min-w-[180px]">
            <div className="flex justify-between items-center mb-2">
              <span className="text-white/80 text-sm font-medium">Deepfake</span>
              <span className="text-white font-bold">{Math.round(scores.deepfake * 100)}%</span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-purple-400 to-purple-500"
                initial={{ width: "0%" }}
                animate={{ width: `${scores.deepfake * 100}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
