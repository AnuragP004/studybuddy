# frontend/Dockerfile
FROM node:20

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN npm run build

# Use a simple static server
RUN npm install -g serve
CMD ["serve", "-s", "dist", "-l", "3000"]
