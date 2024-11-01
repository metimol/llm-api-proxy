import os
import sys
import asyncio
import signal

if not os.path.exists('./data'):
    os.mkdir('./data')

from free_one_api.impls import app

async def shutdown(signal, loop, app):
    """Cleanup coroutine that is called when the application is shutting down."""
    print(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    for task in tasks:
        task.cancel()
    
    print(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

def handle_exception(loop, context):
    """Exception handler for the event loop."""
    msg = context.get("exception", context["message"])
    print(f"Error in async loop: {msg}")

async def main():
    # Set up event loop with custom exception handler
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(handle_exception)
    
    # Create and initialize application
    application = await app.make_application("./data/config.yaml")
    
    # Set up signal handlers
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, 
            lambda s=s: asyncio.create_task(shutdown(s, loop, application))
        )
    
    try:
        await application.run()
        # Keep the application running
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        print("Application shutdown beginning...")
    finally:
        print("Application shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Received keyboard interrupt, shutting down...")