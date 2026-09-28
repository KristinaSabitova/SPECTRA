# syntax=docker/dockerfile:1

# ─────────────── Etapa 1: build ───────────────
# Vite 8 requiere Node ^20.19 || >=22.12
FROM node:22-alpine AS build

WORKDIR /app

# Instalación reproducible desde el lockfile (npm ci, no npm install)
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ─────────────── Etapa 2: runtime ───────────────
# Imagen oficial de nginx que corre como UID 101 (nginx) y escucha en 8080.
# No hay Node, ni node_modules, ni código fuente: solo los estáticos de dist/.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

USER root
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf
USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
