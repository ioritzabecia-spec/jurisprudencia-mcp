# Servidor MCP de jurisprudencia (CENDOJ) y legislación (BOE) para Claude

# Etapa 1: Node.js 22 + puente stdio -> HTTP (supergateway)
FROM node:22-slim AS node
RUN npm install -g supergateway@4

# Etapa 2: Python + Chromium (necesario para el CENDOJ)
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/supergateway /usr/local/lib/node_modules/supergateway
RUN ln -s /usr/local/lib/node_modules/supergateway/dist/index.js /usr/local/bin/supergateway \
    && chmod +x /usr/local/bin/supergateway \
    && apt-get update && apt-get install -y --no-install-recommends git python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Servidor del CENDOJ
RUN git clone --depth 1 https://github.com/ComputingVictor/MCP-CENDOJ.git /opt/cendoj \
    && pip install --no-cache-dir --break-system-packages -r /opt/cendoj/requirements.txt \
    && python3 -m playwright install --with-deps chromium

# Servidor del BOE, en un entorno aparte (usa una versión de la librería mcp distinta a la del CENDOJ)
RUN python3 -m venv /opt/boe \
    && /opt/boe/bin/pip install --no-cache-dir "mcp<2" git+https://github.com/ComputingVictor/MCP-BOE.git

COPY servers.json /opt/servers.json

ENV CENDOJ_HEADLESS=true
EXPOSE 7860

# La clave de acceso se toma de la variable secreta MCP_API_KEY
CMD ["sh", "-c", "supergateway --config /opt/servers.json --port ${PORT:-7860} --apiKey \"$MCP_API_KEY\" --healthEndpoint /healthz"]
