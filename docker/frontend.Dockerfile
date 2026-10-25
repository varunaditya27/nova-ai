# syntax=docker/dockerfile:1
# Nova AI frontend — Next.js standalone server image (shape follows the official with-docker example).
# The build context is frontend/ (the repo-root .dockerignore excludes it); docker-compose sets that up:
#   docker compose -f docker/docker-compose.yml --profile app build frontend
ARG NODE_VERSION=24-slim

FROM node:${NODE_VERSION} AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

FROM node:${NODE_VERSION} AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# next.config.ts rewrites() are fixed at build time, so the backend address is baked in here.
ARG NEXT_PUBLIC_API_BASE
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
RUN npm run build

FROM node:${NODE_VERSION} AS run
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
# The standalone server serves public/ and .next/static only if they are copied next to it.
COPY --from=build --chown=node:node /app/public ./public
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
