# dayribbon frontend — Vite 빌드 + nginx 정적 서빙
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# API 서버 주소를 빌드 시점에 주입 (예: --build-arg VITE_API_BASE=https://api.example.com)
ARG VITE_API_BASE=
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
