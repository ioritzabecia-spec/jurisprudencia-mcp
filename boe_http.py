# Arranca el servidor del BOE una sola vez y lo mantiene vivo (HTTP local, puerto 8002)
import contextlib, uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp_boe.server import BOEMCPServerWithConfig, BOEMCPConfig

cfg = BOEMCPConfig()
cfg.configure_logging()
srv = BOEMCPServerWithConfig(cfg)
manager = StreamableHTTPSessionManager(app=srv.server, stateless=True, json_response=True)

@contextlib.asynccontextmanager
async def lifespan():
    await srv.initialize()
    async with manager.run():
        yield
    await srv.cleanup()

async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        msg = await receive()
        cm = lifespan()
        await cm.__aenter__()
        await send({"type": "lifespan.startup.complete"})
        await receive()
        await cm.__aexit__(None, None, None)
        await send({"type": "lifespan.shutdown.complete"})
        return
    await manager.handle_request(scope, receive, send)

uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
