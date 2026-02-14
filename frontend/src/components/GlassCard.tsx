"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}

export default function GlassCard({ children, className = "", hover = false }: GlassCardProps) {
  return (
    <motion.div
      className={`
        relative overflow-hidden rounded-2xl
        bg-gradient-to-br from-white/10 to-white/5
        backdrop-blur-xl
        border border-white/20
        shadow-2xl
        ${className}
      `}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={hover ? { scale: 1.02, y: -5 } : {}}
      transition={{ duration: 0.3 }}
    >
      {/* Animated gradient overlay */}
      <motion.div
        className="absolute inset-0 opacity-30"
        style={{
          background: "radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.1), transparent 70%)",
        }}
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.3, 0.5, 0.3],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      {/* Content */}
      <div className="relative z-10">{children}</div>

      {/* Shine effect */}
      <motion.div
        className="absolute inset-0 opacity-0"
        style={{
          background:
            "linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.1) 50%, transparent 70%)",
        }}
        whileHover={{ opacity: 1, x: ["0%", "200%"] }}
        transition={{ duration: 0.6 }}
      />
    </motion.div>
  );
}
