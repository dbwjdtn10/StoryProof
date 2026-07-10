# StoryProof Frontend (Vite 빌드 → Nginx 서빙)

FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
# vite.config.ts의 outDir이 'build'로 설정되어 있음 (dist 아님)
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
