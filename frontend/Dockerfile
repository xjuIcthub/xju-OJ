FROM node:14.21.3-buster AS build

WORKDIR /src

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY . ./
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}
RUN yarn run build:ci

FROM nginx:1.27-alpine

COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist/ /usr/share/nginx/html/

EXPOSE 80
