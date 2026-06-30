"""Manual smoke test for the media router — checks availability and exercises whichever
providers have keys set. ComfyUI/FLUX needs ComfyUI running + workflow files in
app/media/workflows/ (see that folder's README) to actually pass; everything else just
needs its API key in .env.

Run from the backend directory with the venv active:
    cd D:\\Projects\\atlas\\backend
    venv\\Scripts\\activate
    python -m tests.test_media
"""
import asyncio

from app.media.router import media_router


async def main():
    print("--- availability ---")
    print(f"ComfyUI (FLUX local): {await media_router.comfyui.is_available()}")
    print(f"GPT Image (OpenAI):  {media_router.gpt_image.is_available()}")
    print(f"Ideogram:            {media_router.ideogram.is_available()}")
    print(f"RunwayML Gen-3:      {media_router.runway.is_available()}")
    print(f"ElevenLabs:          {media_router.elevenlabs.is_available()}")

    print("\n--- image (auto: FLUX local -> DALL-E 3 fallback) ---")
    try:
        result = await media_router.image("a small terracotta robot watering a plant, studio lighting")
        print(f"[{result['provider']}] saved to {result['path']} ({len(result['bytes'])} bytes)")
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- audio (ElevenLabs) ---")
    try:
        result = await media_router.audio("Atlas Phase 4 smoke test.")
        print(f"[{result['provider']}] saved to {result['path']} ({len(result['bytes'])} bytes)")
    except Exception as e:
        print(f"FAILED (is ELEVENLABS_API_KEY set?): {e}")

    # Video skipped by default — Gen-3 needs a source image URL and costs real money per
    # call. Uncomment and supply a real image_url to test it.
    # print("\n--- video (RunwayML Gen-3) ---")
    # try:
    #     result = await media_router.video("camera slowly pans left", image_url="https://example.com/frame.png")
    #     print(f"[{result['provider']}] saved to {result['path']} ({len(result['bytes'])} bytes)")
    # except Exception as e:
    #     print(f"FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(main())
