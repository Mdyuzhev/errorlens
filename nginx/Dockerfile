FROM nginx:alpine

# Copy nginx config (context is project root)
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy static files
COPY landing /usr/share/nginx/html/
COPY bookmarklet /usr/share/nginx/html/bookmarklet/
COPY dashboard /usr/share/nginx/html/dashboard/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
