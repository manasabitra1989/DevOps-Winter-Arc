# Stage 1: Build the website
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json build.js ./
COPY src/ ./src/

RUN npm run build


# Stage 2: Serve the website
FROM nginx:alpine

COPY --from=builder /app/dist/ /usr/share/nginx/html/

EXPOSE 80
