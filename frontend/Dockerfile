FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ENV NEXT_PUBLIC_API_URL=http://localhost:8000
EXPOSE 3000

# Dev server for the local-first workflow; swap to `npm run build && npm start`
# for a production image.
CMD ["npm", "run", "dev"]
