import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const store = mutation({
  args: {
    session_id: v.string(),
    token: v.string(),
    issued_at: v.number(),
    expires_at: v.number(),
  },
  handler: async (ctx, args) => {
    await ctx.db.insert("tokens", args);
  },
});

export const get = query({
  args: { token: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("tokens")
      .withIndex("by_token", (q) => q.eq("token", args.token))
      .first();
  },
});

export const getBySession = query({
  args: { session_id: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("tokens")
      .withIndex("by_session", (q) => q.eq("session_id", args.session_id))
      .first();
  },
});
