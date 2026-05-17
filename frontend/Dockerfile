# ─── Stage 1: TypeScript → JavaScript ────────────────────────────────────────
FROM node:20-alpine AS ts-build

WORKDIR /build

COPY frontend/package.json frontend/tsconfig.json ./
RUN npm install --include=dev

COPY frontend/ts/ ./ts/
RUN npm run build

# ─── Stage 2: nginx serving static files ─────────────────────────────────────
FROM nginx:alpine

COPY frontend/index.html frontend/style.css /usr/share/nginx/html/
COPY --from=ts-build /build/js/ /usr/share/nginx/html/js/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1
