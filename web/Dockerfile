# Use the specific Node version from your machine
FROM node:25.2.1

WORKDIR /app

# Copy package files first to leverage Docker cache
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Vite requires --host to be accessible outside the container
CMD ["npm", "run", "dev", "--", "--host"]