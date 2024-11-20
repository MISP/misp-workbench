# build frontend
FROM node:18-alpine AS builder

WORKDIR /code

COPY package*.json ./
RUN npm install --omit=dev
RUN npm install npm-run-all

COPY . .

RUN npm run build

FROM nginx:alpine AS frontend
COPY ./nginx.conf /etc/nginx/nginx.conf

RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /code/dist /usr/share/nginx/html
