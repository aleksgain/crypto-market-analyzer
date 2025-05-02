FROM node:18-alpine

WORKDIR /app

# Copy package.json files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Create a basic react-scripts structure if it doesn't exist
RUN npm install -g create-react-app

# Copy the rest of the app
COPY . .

# Fix for create-react-app in Docker
ENV CI=false
ENV WDS_SOCKET_PORT=0

EXPOSE 3000

# Make sure node_modules/.bin is in PATH
ENV PATH /app/node_modules/.bin:$PATH

CMD ["npm", "start"] 