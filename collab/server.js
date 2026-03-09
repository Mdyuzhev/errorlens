import { Hocuspocus } from "@hocuspocus/server";
import { Redis } from "@hocuspocus/extension-redis";
import { Database } from "@hocuspocus/extension-database";
import axios from "axios";

const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";
const REDIS_HOST = process.env.REDIS_HOST || "redis";
const REDIS_PORT = parseInt(process.env.REDIS_PORT || "6379", 10);
const PORT = parseInt(process.env.PORT || "1234", 10);

const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 10000,
});

const server = new Hocuspocus({
  port: PORT,
  extensions: [
    new Redis({
      host: REDIS_HOST,
      port: REDIS_PORT,
    }),
    new Database({
      fetch: async ({ documentName }) => {
        // documentName = "article:{slug}"
        const slug = documentName.replace("article:", "");
        try {
          const res = await api.get(`/api/v1/articles/by-slug/${slug}`);
          const content = res.data?.content;
          if (content) {
            // Return as Uint8Array for Yjs
            return new Uint8Array(Buffer.from(JSON.stringify(content)));
          }
        } catch (err) {
          console.error(`[fetch] Failed to load article ${slug}:`, err.message);
        }
        return null;
      },
      store: async ({ documentName, state }) => {
        const slug = documentName.replace("article:", "");
        try {
          const content = JSON.parse(Buffer.from(state).toString());
          await api.put(`/api/v1/articles/by-slug/${slug}`, { content });
        } catch (err) {
          console.error(`[store] Failed to save article ${slug}:`, err.message);
        }
      },
    }),
  ],

  async onAuthenticate(data) {
    const token = data.token;
    if (!token) {
      throw new Error("Authentication required");
    }
    try {
      const res = await api.get("/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      return { user: res.data };
    } catch (err) {
      throw new Error("Invalid token");
    }
  },
});

server.listen().then(() => {
  console.log(`Hocuspocus collab server running on port ${PORT}`);
});
