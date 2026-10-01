import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// 开发期：/api 代理到 FastAPI，使用 credentials: include。
// 生产：同源反代 —— React 占 /，FastAPI 占 /api（SOFTWARE_DESIGN.md §7）。
export default defineConfig(({ mode }) => {
  const target = loadEnv(mode, ".", "STUDYPLAN_").STUDYPLAN_API_URL || "http://127.0.0.1:8000";
  return {
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/healthz": { target },
      "/api": {
        target,
        changeOrigin: false,
        // Cookie 必须在开发期正确透传（AuthContext 来自签名会话）
        cookieDomainRewrite: "localhost",
      },
    },
  },
  };
});
