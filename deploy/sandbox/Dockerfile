FROM mcr.microsoft.com/playwright:v1.57.0-noble@sha256:3bed4b1a12f2338642f3d8cba28e291deef3c66bd4a964bbeb3e57bbff511dbd
WORKDIR /opt/repropatch
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
ENV NODE_PATH=/opt/repropatch/node_modules
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY serve.cjs run-test.cjs /opt/repropatch/
