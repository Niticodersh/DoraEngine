FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Expose port
EXPOSE 5173

# Run Vite dev server with host exposure
CMD ["npm", "run", "dev", "--", "--host"]
