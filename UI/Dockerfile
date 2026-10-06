FROM node:20-alpine

WORKDIR /app

# Install deps first for layer caching (same trick as the backend Dockerfile).
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]