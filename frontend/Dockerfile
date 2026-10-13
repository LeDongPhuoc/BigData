FROM node:24.15.0-alpine@sha256:8e2c930fda481a6ec141fe5a88e8c249c69f8102fe98af505f38c081649ea749 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY . .
RUN npm run build

FROM nginx:1.30.0-alpine@sha256:e544ba68e68ddbcdff106010fa82f4ab30378899e78d4ff7aadf4ef5a7c65091
# Apply vendor security updates within the base image's existing Alpine release.
# The deployed image digest and package/CVE inventory are retained in QA reports.
RUN apk upgrade --no-cache
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
