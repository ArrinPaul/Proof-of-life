import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  sessions: defineTable({
    session_id: v.string(), // backend-generated UUID
    user_id: v.string(),
    status: v.string(), // "active", "completed", "timeout", "failed"
    start_time: v.number(),
    end_time: v.optional(v.number()),
    failed_count: v.number(),
  })
    .index("by_session_id", ["session_id"])
    .index("by_user", ["user_id"])
    .index("by_status", ["status"]),

  verification_results: defineTable({
    session_id: v.string(),
    liveness_score: v.number(),
    emotion_score: v.number(),
    deepfake_score: v.number(),
    final_score: v.number(),
    passed: v.boolean(),
    timestamp: v.number(),
  }).index("by_session", ["session_id"]),

  tokens: defineTable({
    session_id: v.string(),
    token: v.string(),
    issued_at: v.number(),
    expires_at: v.number(),
  })
    .index("by_token", ["token"])
    .index("by_session", ["session_id"]),

  nonces: defineTable({
    session_id: v.string(),
    nonce: v.string(),
    expires_at: v.number(),
    used: v.boolean(),
  })
    .index("by_nonce", ["nonce"])
    .index("by_expiry", ["expires_at"])
    .index("by_session", ["session_id"]),

  audit_logs: defineTable({
    session_id: v.optional(v.string()),
    user_id: v.optional(v.string()),
    event_type: v.string(),
    timestamp: v.number(),
    details: v.optional(v.string()),
  })
    .index("by_session", ["session_id"])
    .index("by_user", ["user_id"])
    .index("by_timestamp", ["timestamp"])
    .index("by_event_type", ["event_type"]),
});
