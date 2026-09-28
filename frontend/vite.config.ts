import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// El dev server SOLO se usa en local. En producción se sirve `dist/` como
// estático detrás de nginx (ver Dockerfile multi-stage). Nunca exponer
// este servidor a Internet: permite leer ficheros vía /@fs.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    host: '127.0.0.1',
    port: 3000,
    strictPort: true,
    // Solo responder a Host conocidos (evita DNS-rebinding contra el dev server).
    allowedHosts: ['localhost', '127.0.0.1'],
    fs: {
      strict: true,
      allow: [path.resolve(import.meta.dirname)],
      deny: ['**/.env', '**/.env.*', '**/.git/**', '**/*.pem', '**/*.key', '**/.ssh/**', '**/.aws/**'],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
