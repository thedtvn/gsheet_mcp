import sys
import click
import uvicorn
from .core import mcp_server
from starlette.applications import Starlette

def eprint(*args, **kwargs):
    """
    Print function that can be used to print stderr messages in MCP server mode stdio.
    """
    print(*args, file=sys.stderr, **kwargs)

@click.command()
@click.option("--port", default=3000, help="Port to run the MCP server SSE mode. Default is 3000.")
@click.option("--host", default="localhost", help="Host to run the MCP server SSE mode. Default is localhost.")
@click.option("--sse", is_flag=True, help="Run the MCP server in SSE and Streamable HTTP mode. Default is Stdio mode.")
def main(port: int, host: str, sse: bool):
    # check if the client is valid
    if sse:
        streamable_http_app = mcp_server.streamable_http_app()
        sse_app = mcp_server.sse_app()
        async def lifespan(app):
            print("MCP server started in SSE mode.")
            print(f"You can access the SSE: http://{host}:{port}/sse")
            print(f"or streamable http: http://{host}:{port}/mcp")
            async with sse_app.router.lifespan_context(app), streamable_http_app.router.lifespan_context(app):
                yield
        starlette_app = Starlette(
            routes=streamable_http_app.routes + sse_app.routes,
            middleware=streamable_http_app.user_middleware + sse_app.user_middleware,
            lifespan=lifespan,
        )
        config = uvicorn.Config(
            starlette_app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
    else:
        eprint("Start Stdio server")
        mcp_server.run("stdio")


if __name__ == "__main__":
    main()
