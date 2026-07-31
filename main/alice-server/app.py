import sys
import uuid
import signal
import asyncio
from aioconsole import ainput
from config.settings import load_config
from config.logger import setup_logging
from core.utils.util import get_local_ip, validate_mcp_endpoint
from core.http_server import SimpleHttpServer
from core.websocket_server import WebSocketServer
from core.utils.util import check_ffmpeg_installed
from core.utils.gc_manager import get_gc_manager

TAG = __name__
logger = setup_logging()


async def wait_for_exit() -> None:
    """
    Block until Ctrl‑C or SIGTERM is received.
    - Unix: use add_signal_handler
    - Windows: rely on KeyboardInterrupt
    """
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    if sys.platform != "win32":  # Unix / macOS
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
        await stop_event.wait()
    else:
        # Windows: await a future that never completes,
        # so KeyboardInterrupt can bubble up to asyncio.run and avoid shutdown blocking caused by lingering normal threads
        try:
            await asyncio.Future()
        except KeyboardInterrupt:  # Ctrl‑C
            pass


async def monitor_stdin():
    """Monitor standard input and consume Enter key presses."""
    while True:
        await ainput()  # Wait asynchronously for input and consume the Enter key


async def main():
    check_ffmpeg_installed()
    config = await load_config()

    # auth_key priority: config server.auth_key > manager-api.secret > auto-generated
    # auth_key is used for JWT authentication, including the vision analysis interface, OTA token generation, and WebSocket authentication
    # Get auth_key from the config file
    auth_key = config["server"].get("auth_key", "")
    
    # Validate auth_key; if invalid, try manager-api.secret
    if not auth_key or len(auth_key) == 0 or "you" in auth_key:
        auth_key = config.get("manager-api", {}).get("secret", "")
        # Validate the secret; if invalid, generate a random key
        if not auth_key or len(auth_key) == 0 or "you" in auth_key:
            auth_key = str(uuid.uuid4().hex)
    
    config["server"]["auth_key"] = auth_key

    # Add the stdin monitoring task
    stdin_task = asyncio.create_task(monitor_stdin())

    # Start the global GC manager (cleanup every 5 minutes)
    gc_manager = get_gc_manager(interval_seconds=300)
    await gc_manager.start()

    # Start the WebSocket server
    ws_server = WebSocketServer(config)
    ws_task = asyncio.create_task(ws_server.start())
    # Start the Simple HTTP server
    ota_server = SimpleHttpServer(config)
    ota_task = asyncio.create_task(ota_server.start())

    read_config_from_api = config.get("read_config_from_api", False)
    port = int(config["server"].get("http_port", 8003))
    if not read_config_from_api:
        logger.bind(tag=TAG).info(
            "OTA interface is\t\thttp://{}:{}/xiaozhi/ota/",
            get_local_ip(),
            port,
        )
    logger.bind(tag=TAG).info(
        "Vision analysis interface is\thttp://{}:{}/mcp/vision/explain",
        get_local_ip(),
        port,
    )
    mcp_endpoint = config.get("mcp_endpoint", None)
    if mcp_endpoint is not None and "you" not in mcp_endpoint:
        # Validate the MCP endpoint format
        if validate_mcp_endpoint(mcp_endpoint):
            logger.bind(tag=TAG).info("MCP endpoint is\t{}", mcp_endpoint)
            # Convert the MCP endpoint address to the call endpoint
            mcp_endpoint = mcp_endpoint.replace("/mcp/", "/call/")
            config["mcp_endpoint"] = mcp_endpoint
        else:
            logger.bind(tag=TAG).error("The MCP endpoint format is invalid")
            config["mcp_endpoint"] = "Your MCP endpoint WebSocket address"

    # Get the WebSocket configuration with a safe default value
    websocket_port = 8000
    server_config = config.get("server", {})
    if isinstance(server_config, dict):
        websocket_port = int(server_config.get("port", 8000))

    logger.bind(tag=TAG).info(
        "WebSocket address is\tws://{}:{}/xiaozhi/v1/",
        get_local_ip(),
        websocket_port,
    )

    logger.bind(tag=TAG).info(
        "=======The address above is the WebSocket protocol address; do not open it in a browser======="
    )
    logger.bind(tag=TAG).info(
        "To test WebSocket, start the digital-human module and open the browser interaction test"
    )
    logger.bind(tag=TAG).info(
        "=============================================================\n"
    )

    try:
        await wait_for_exit()  # Block until an exit signal is received
    except asyncio.CancelledError:
        print("Task cancelled; cleaning up resources...")
    finally:
        # Stop the global GC manager
        await gc_manager.stop()

        # Cancel all tasks (key fix)
        stdin_task.cancel()
        ws_task.cancel()
        if ota_task:
            ota_task.cancel()

        # Wait for tasks to stop (a timeout is required)
        await asyncio.wait(
            [stdin_task, ws_task, ota_task] if ota_task else [stdin_task, ws_task],
            timeout=3.0,
            return_when=asyncio.ALL_COMPLETED,
        )
        print("Server shut down; exiting the program.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted manually; terminating the program.")
