import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const create = mutation({
  args: {
    user_id: v.string(),
  },
  handler: async (ctx, args) => {
    const sessionId = await ctx.db.insert("sessions", {
      user_id: args.user_id,
      status: "active",
      start_time: Date.now(),
      failed_count: 0,
    });
    return sessionId;
  },
});

export const get = query({
  args: { id: v.id("sessions") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.id);
  },
});

export const getByUser = query({
  args: { user_id: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("sessions")
      .withIndex("by_user", (q) => q.eq("user_id", args.user_id))
      .order("desc")
      .first();
  },
});

export const update = mutation({
  args: {
    id: v.id("sessions"),
    status: v.optional(v.string()),
    failed_count: v.optional(v.number()),
    end_time: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const { id, ...updates } = args;
    await ctx.db.patch(id, updates);
  },
});

export const checkTimeout = query({
  args: { id: v.id("sessions") },
  handler: async (ctx, args) => {
    const session = await ctx.db.get(args.id);
    if (!session) return true;
    
    const elapsed = Date.now() - session.start_time;
    return elapsed > 120000; // 2 minutes
  },
});

export const terminate = mutation({
  args: {
    id: v.id("sessions"),
    reason: v.string(),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, {
      status: args.reason,
      end_time: Date.now(),
    });
  },
});
