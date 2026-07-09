FROM node:26-alpine AS deps

WORKDIR /app
ARG NPM_CONFIG_REGISTRY=https://registry.npmmirror.com/

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci --registry="$NPM_CONFIG_REGISTRY"


FROM node:26-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AUTH_REQUIRED=0
ENV NEXT_PUBLIC_AUTH_REQUIRED=$NEXT_PUBLIC_AUTH_REQUIRED
ARG NEXT_PUBLIC_SITE_URL=https://keeltrader.joyeeassets.com
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build


FROM node:26-alpine AS runner

WORKDIR /app
ARG NPM_CONFIG_REGISTRY=https://registry.npmmirror.com/

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AUTH_REQUIRED=0
ENV NEXT_PUBLIC_AUTH_REQUIRED=$NEXT_PUBLIC_AUTH_REQUIRED
ARG NEXT_PUBLIC_SITE_URL=https://keeltrader.joyeeassets.com
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL

# Install only production dependencies
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --registry="$NPM_CONFIG_REGISTRY" && npm cache clean --force

# Copy build output and source files
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
# Copy app directory for runtime
COPY --from=builder /app/app ./app
COPY --from=builder /app/proxy.ts ./proxy.ts

EXPOSE 3000

CMD ["npm", "start", "--", "-p", "3000", "-H", "0.0.0.0"]
