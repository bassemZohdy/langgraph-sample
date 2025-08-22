# --- Build stage ---
FROM node:18-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* .npmrc* ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

# --- Run stage ---
FROM nginx:alpine
WORKDIR /usr/share/nginx/html
COPY --from=build /app/dist ./

# Runtime env -> config.js generator
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Basic nginx config (serve single page app)
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

ENV UI_API_BASE_URL=/api

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
