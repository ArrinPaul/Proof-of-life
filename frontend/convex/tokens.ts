import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const store = mutation({
  args: {
    session_id: v.string(),
    token: v.string(),
    issued_at: v.number(),
    expires_at: v.number(),
    token_id: v.optional(v.string()),
    user_id: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    await ctx.db.insert("tokens", {
      session_id: args.session_id,
      token: args.token,
      issued_at: args.issued_at,
      expires_at: args.expires_at,
    });
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
