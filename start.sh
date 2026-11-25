#!/bin/sh
# 1. Arranca los dos servidores una sola vez y los deja vivos
python3 /opt/cendoj_http.py &
/opt/boe/bin/python /opt/boe_http.py &
# 2. Espera a que respondan
for i in $(seq 1 120); do
  curl -s -o /dev/null http://127.0.0.1:8001/mcp && curl -s -o /dev/null http://127.0.0.1:8002/mcp && break
  sleep 1
done
# 3. Publica ambos bajo una dirección que incluye la clave secreta
sed "s|CLAVE_SECRETA|$MCP_API_KEY|g" /opt/servers.json > /tmp/servers.json
exec supergateway --config /tmp/servers.json --port "${PORT:-7860}" --healthEndpoint /healthz
