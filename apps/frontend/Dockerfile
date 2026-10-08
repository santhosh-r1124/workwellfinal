FROM node:22-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3300

CMD ["npm", "run", "dev"]
