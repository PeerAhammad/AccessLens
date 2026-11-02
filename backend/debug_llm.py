import asyncio
import traceback
from app.llm import default_call, PROVIDER, MODEL

async def main():
    print("provider:", PROVIDER, "| model:", MODEL)
    try:
        print(await default_call("Reply with only the word OK", "hi", None))
    except Exception:
        traceback.print_exc()

asyncio.run(main())
