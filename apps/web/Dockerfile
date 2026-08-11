# syntax=docker/dockerfile:1
# Build the static bundle, then serve it from nginx (which also proxies the API,
# so the browser makes same-origin requests and no CORS or API base URL is needed).

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
