FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --silent

FROM node:18-alpine AS build
WORKDIR /app
# Accept build-time Vite API URL and expose it to the build environment
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
RUN npm install -g serve --silent
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
