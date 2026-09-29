import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发期：/api 代理到 FastAPI，使用 credentials: include。
// 生产：同源反代 —— React 占 /，FastAPI 占 /api（SOFTWARE_DESIGN.md §7）。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/healthz": {target:"http://127.0.0.1:8000"},
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
        // Cookie 必须在开发期正确透传（AuthContext 来自签名会话）
        cookieDomainRewrite: "localhost",
      },
    },
  },
});
