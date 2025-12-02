FROM nginx:alpine

# Copy viewer files
COPY index.html /usr/share/nginx/html/
COPY viewer.js /usr/share/nginx/html/
COPY service-worker.js /usr/share/nginx/html/
COPY manifest.json /usr/share/nginx/html/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
