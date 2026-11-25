# Arranca el servidor del CENDOJ una sola vez y lo mantiene vivo (HTTP local, puerto 8001)
import sys, uvicorn
sys.path.insert(0, "/opt/cendoj")
sys.path.insert(0, "/opt")
import cendoj_patch  # arreglo de la descarga de PDF
from app.mcp_server import mcp
app = mcp.http_app(path="/mcp", stateless_http=True)
uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
