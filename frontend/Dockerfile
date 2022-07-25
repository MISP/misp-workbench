# build frontend
FROM node:16-alpine as builder

WORKDIR /code

COPY package*.json ./
RUN npm install --omit=dev

COPY . .

RUN npm run build

FROM nginx:alpine as frontend
COPY ./nginx.conf /etc/nginx/nginx.conf

RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /code/dist /usr/share/nginx/html
