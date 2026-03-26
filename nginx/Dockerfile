# Stage 1: Build Vue dashboard
FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY dashboard-vue/package.json dashboard-vue/package-lock.json ./
RUN npm ci --prefer-offline
COPY dashboard-vue/ ./

ENV VITE_BASE=/dashboard/
ENV VITE_API_URL=/api
RUN npm run build

# Stage 2: Nginx with static files
FROM nginx:alpine

COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Landing page (accessible at /landing/)
COPY landing/ /usr/share/nginx/html/landing/

# Bookmarklet scripts
COPY bookmarklet/recorder.js /usr/share/nginx/html/bookmarklet/
COPY bookmarklet/recorder.min.js /usr/share/nginx/html/bookmarklet/

# Vue dashboard from stage 1
COPY --from=frontend-builder /build/dist /usr/share/nginx/html/dashboard-vue/dist/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
