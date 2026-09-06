FROM node:22-alpine
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY apps/web ./
RUN npm run build
EXPOSE 8301
CMD ["npm", "run", "start"]
