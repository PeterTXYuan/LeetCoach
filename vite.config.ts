import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        sidePanel: "sidePanel.html",
        background: "src/background.ts"
      },
      output: {
        entryFileNames: "[name].js"
      }
    }
  }
});
