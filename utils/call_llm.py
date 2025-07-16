from google import genai

from config import settings


def call_llm(prompt: str) -> str:
    client = genai.Client(
        api_key=settings.google_gemini_genai_api_token,
    )
    model = settings.google_gemini_genai_model
    response = client.models.generate_content(model=model, contents=[prompt])
    return response.text


async def stream_llm(prompt: str):
    client = genai.Client(
        api_key=settings.google_gemini_genai_api_token,
    )
    model = settings.google_gemini_genai_model
    response = await client.aio.models.generate_content_stream(
        model=model, contents=[prompt]
    )
    async for chunk in response:
        yield chunk.text


if __name__ == "__main__":
    import asyncio

    test_prompt = "DRS in F1 racing?"

    # First call - should hit the API
    print("Making call...")

    async def main():
        async for chunk in stream_llm(test_prompt):
            print(f"Response: {chunk}")

    asyncio.run(main())
