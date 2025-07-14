from google import genai

from config import settings


def call_llm(prompt: str) -> str:
    client = genai.Client(
        api_key=settings.google_gemini_genai_api_token,
    )
    model = settings.google_gemini_genai_model
    response = client.models.generate_content(model=model, contents=[prompt])
    return response.text


if __name__ == "__main__":
    test_prompt = "Hello, how are you?"

    # First call - should hit the API
    print("Making call...")
    response1 = call_llm(test_prompt)
    print(f"Response: {response1}")
