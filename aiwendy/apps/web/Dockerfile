FROM docker.1ms.run/library/node:20-alpine AS deps

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci


FROM docker.1ms.run/library/node:20-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AUTH_REQUIRED=0
ENV NEXT_PUBLIC_AUTH_REQUIRED=$NEXT_PUBLIC_AUTH_REQUIRED
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build


FROM docker.1ms.run/library/node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

ARG NEXT_PUBLIC_API_URL=http://api:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AUTH_REQUIRED=0
ENV NEXT_PUBLIC_AUTH_REQUIRED=$NEXT_PUBLIC_AUTH_REQUIRED

# Install only production dependencies
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Copy build output and source files
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
# Copy app directory for runtime
COPY --from=builder /app/app ./app

EXPOSE 3000

CMD ["npm", "start", "--", "-p", "3000", "-H", "0.0.0.0"]

