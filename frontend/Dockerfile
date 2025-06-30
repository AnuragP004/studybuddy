FROM node:20-alpine AS builder

WORKDIR /app
COPY . .
RUN npm install && npm run build

# Serve the built frontend
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
