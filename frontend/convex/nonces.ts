import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const store = mutation({
  args: {
    session_id: v.string(),
    nonce: v.string(),
    expires_at: v.number(),
  },
  handler: async (ctx, args) => {
    await ctx.db.insert("nonces", {
      session_id: args.session_id,
      nonce: args.nonce,
      expires_at: args.expires_at,
      used: false,
    });
  },
});

export const exists = query({
  args: { nonce: v.string() },
  handler: async (ctx, args) => {
    const nonceRecord = await ctx.db
      .query("nonces")
      .withIndex("by_nonce", (q) => q.eq("nonce", args.nonce))
      .first();
    return !!nonceRecord;
  },
});

export const validate = query({
  args: {
    session_id: v.string(),
    nonce: v.string(),
  },
  handler: async (ctx, args) => {
    const nonceRecord = await ctx.db
      .query("nonces")
      .withIndex("by_nonce", (q) => q.eq("nonce", args.nonce))
      .first();

    if (!nonceRecord) return false;
    if (nonceRecord.used) return false;
    if (nonceRecord.session_id !== args.session_id) return false;
    if (Date.now() > nonceRecord.expires_at) return false;

    return true;
  },
});

export const markUsed = mutation({
  args: {
    nonce: v.string(),
  },
  handler: async (ctx, args) => {
    const nonceRecord = await ctx.db
      .query("nonces")
      .withIndex("by_nonce", (q) => q.eq("nonce", args.nonce))
      .first();

    if (nonceRecord) {
      await ctx.db.patch(nonceRecord._id, { used: true });
    }
  },
});

export const purgeExpired = mutation({
  handler: async (ctx) => {
    const now = Date.now();
    const expired = await ctx.db
      .query("nonces")
      .withIndex("by_expiry")
      .filter((q) => q.lt(q.field("expires_at"), now))
      .collect();

    for (const nonce of expired) {
      await ctx.db.delete(nonce._id);
    }

    return expired.length;
  },
});
