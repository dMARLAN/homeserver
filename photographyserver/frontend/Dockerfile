FROM node:18-alpine

WORKDIR /app

# Copy package files from the correct path
COPY photographyserver/frontend/package*.json ./
RUN npm ci

# Copy frontend source code
COPY photographyserver/frontend/ .

EXPOSE 3000

CMD ["npm", "run", "dev"]
