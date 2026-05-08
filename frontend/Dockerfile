# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* yarn.lock* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build && \
    ls -la dist/ && \
    echo "Build complete: $(ls -1 dist/ | wc -l) files generated"

# Runtime stage
FROM node:20-alpine

WORKDIR /app

# Install serve to run the production build
RUN npm install -g serve

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create non-root user
RUN addgroup -g 1001 officejoe && \
    adduser -D -u 1001 -G officejoe officejoe

# Change ownership of app directory
RUN chown -R officejoe:officejoe /app

# Switch to non-root user
USER officejoe

EXPOSE 3000

# Healthcheck: verify index.html exists in dist
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD test -f /app/dist/index.html || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
