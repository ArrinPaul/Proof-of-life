import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const log = mutation({
  args: {
    session_id: v.optional(v.string()),
    user_id: v.optional(v.string()),
    event_type: v.string(),
    details: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    await ctx.db.insert("audit_logs", {
      ...args,
      timestamp: Date.now(),
    });
  },
});

export const getBySession = query({
  args: { session_id: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("audit_logs")
      .withIndex("by_session", (q) => q.eq("session_id", args.session_id))
      .order("desc")
      .collect();
  },
});

export const getByUser = query({
  args: { user_id: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("audit_logs")
      .withIndex("by_user", (q) => q.eq("user_id", args.user_id))
      .order("desc")
      .collect();
  },
});

export const getRecent = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = args.limit || 100;
    return await ctx.db
      .query("audit_logs")
      .withIndex("by_timestamp")
      .order("desc")
      .take(limit);
  },
});

export const purgeOld = mutation({
  args: { days: v.number() },
  handler: async (ctx, args) => {
    const cutoff = Date.now() - args.days * 24 * 60 * 60 * 1000;
    const old = await ctx.db
      .query("audit_logs")
      .withIndex("by_timestamp")
      .filter((q) => q.lt(q.field("timestamp"), cutoff))
      .collect();

    for (const log of old) {
      await ctx.db.delete(log._id);
    }

    return old.length;
  },
});
