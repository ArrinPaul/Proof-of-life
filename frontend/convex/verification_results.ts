import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const save = mutation({
  args: {
    session_id: v.string(),
    liveness_score: v.number(),
    emotion_score: v.number(),
    deepfake_score: v.number(),
    final_score: v.number(),
    passed: v.boolean(),
  },
  handler: async (ctx, args) => {
    await ctx.db.insert("verification_results", {
      ...args,
      timestamp: Date.now(),
    });
  },
});

export const getBySession = query({
  args: { session_id: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("verification_results")
      .withIndex("by_session", (q) => q.eq("session_id", args.session_id))
      .first();
  },
});
