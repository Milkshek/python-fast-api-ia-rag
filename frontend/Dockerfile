FROM node:24-bookworm-slim AS development
WORKDIR /workspace
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN chown -R node:node /workspace
USER node
EXPOSE 5173
CMD ["npm", "run", "dev"]
