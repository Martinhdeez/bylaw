# The demo UI (Next.js production build) for the VPS deploy (DP1). Next bakes the /api rewrite at build time,
# and may read it again at start: BYLAW_API_URL is set in both stages, the API's address on the compose network.
FROM node:22.22.0-bookworm-slim AS build
WORKDIR /ui
ENV NEXT_TELEMETRY_DISABLED=1
ARG BYLAW_API_URL=http://bylaw-api:8000
ENV BYLAW_API_URL=$BYLAW_API_URL
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build && npm prune --omit=dev

FROM node:22.22.0-bookworm-slim
WORKDIR /ui
ARG BYLAW_API_URL=http://bylaw-api:8000
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 BYLAW_API_URL=$BYLAW_API_URL
COPY --from=build /ui/package.json /ui/next.config.mjs ./
COPY --from=build /ui/node_modules node_modules
COPY --from=build /ui/.next .next
COPY --from=build /ui/public public
USER node
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
