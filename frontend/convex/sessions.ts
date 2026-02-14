import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const create = mutation({
  args: {
    session_id: v.string(),
    user_id: v.string(),
    start_time: v.number(),
  },
  handler: async (ctx, args) => {
    const id = await ctx.db.insert("sessions", {
      session_id: args.session_id,
      user_id: args.user_id,
      status: "active",
      start_time: args.start_time,
      failed_count: 0,
    });
    return id;
  },
});

export const get = query({
  args: { id: v.id("sessions") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.id);
  },
});

export const getBySessionId = query({
  args: { session_id: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("sessions")
      .withIndex("by_session_id", (q) => q.eq("session_id", args.session_id))
      .first();
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
    const filtered: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(updates)) {
      if (val !== undefined) filtered[k] = val;
    }
    await ctx.db.patch(id, filtered);
  },
});

export const updateBySessionId = mutation({
  args: {
    session_id: v.string(),
    status: v.optional(v.string()),
    failed_count: v.optional(v.number()),
    end_time: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const session = await ctx.db
      .query("sessions")
      .withIndex("by_session_id", (q) => q.eq("session_id", args.session_id))
      .first();
    if (!session) return;
    const updates: Record<string, unknown> = {};
    if (args.status !== undefined) updates.status = args.status;
    if (args.failed_count !== undefined) updates.failed_count = args.failed_count;
    if (args.end_time !== undefined) updates.end_time = args.end_time;
    await ctx.db.patch(session._id, updates);
  },
});

export const checkTimeout = query({
  args: { id: v.id("sessions") },
  handler: async (ctx, args) => {
    const session = await ctx.db.get(args.id);
    if (!session) return true;
    const elapsed = Date.now() - session.start_time;
    return elapsed > 120000;
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
