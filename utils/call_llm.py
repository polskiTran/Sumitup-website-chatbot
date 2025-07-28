from google import genai
from google.genai import types

from config import settings
from helpers.helpers import wave_file


def call_llm(prompt: str) -> str:  # TODO: add type hinting
    """
    Call the LLM and return the response.
    Args:
        prompt: The prompt to send to the LLM.
    Returns:
        The response from the LLM.
    """
    client = genai.Client(
        api_key=settings.google_gemini_genai_api_token,
    )
    model = settings.google_gemini_genai_model
    response = client.models.generate_content(model=model, contents=[prompt])
    return response.text


async def stream_llm(prompt: str) -> str:
    """
    Stream the response from the LLM.
    Args:
        prompt: The prompt to send to the LLM.
    Returns:
        The response from the LLM.
    """
    client = genai.Client(
        api_key=settings.google_gemini_genai_api_token,
    )
    model = settings.google_gemini_genai_model
    response = await client.aio.models.generate_content_stream(
        model=model, contents=[prompt]
    )
    async for chunk in response:
        yield chunk.text


def text_to_speech(text: str) -> bytes:
    """
    Convert text to speech.
    Args:
        text: The text to convert to speech.
    Returns:
        The audio data.
    """
    client = genai.Client(
        api_key=settings.google_gemini_genai_api_token,
    )
    model = settings.google_gemini_text_to_speech_model
    response = client.models.generate_content(
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore",
                    )
                )
            ),
        ),
    )
    return response.candidates[0].content.parts[0].inline_data.data


if __name__ == "__main__":
    # import asyncio

    test_prompt = "DRS in F1 racing?"
    newsletter_response = """
Here are the Ben Lorica newsletters from the past week:

**1. Quick Wins for your AI eval strategy**
_Date:_ July 15, 2025
_Key Finding:_ This newsletter offers a comprehensive guide to AI evaluation strategies, emphasizing the importance of systematically assessing AI-generated outputs for quality, reliability, and business impact. It outlines a roadmap covering foundational principles, operational excellence, and frontier techniques to effectively deploy AI. Key takeaways include establishing evaluation as a first-class engineering discipline, layering multiple evaluation methods, prioritizing reliability over peak performance, implementing dual-track evaluation, building production-to-development feedback loops, integrating human oversight, designing cost-aware practices, evaluating agent workflows holistically, continuously improving evaluation systems, connecting metrics to business outcomes, and documenting practices for governance.
_Read more of the article: [Quick Wins for your AI eval strategy](https://substack.com/app-link/post?publication_id=20983&post_id=167485385&utm_source=post-email-title&utm_campaign=email-post-title&isFreemail=true&r=5s83oz&token=eyJ1c2VyX2lkIjozNDk3MzgxNjMsInBvc3RfaWQiOjE2NzQ4NTM4NSwiaWF0IjoxNzUyNTg4NTcwLCJleHAiOjE3NTUxODA1NzAsImlzcyI6InB1Yi0yMDk4MyIsInN1YiI6InBvc3QtcmVhY3Rpb24ifQ.ZFbDNwQooEmRIoTdObq9ukLgBQX_0qsIEHCFtchn_zQ)_
_Read more of the newsletter: [Ben Lorica - 2025/07/15](https://polskitran.github.io/Sumitup-quartz-dev/2025-07-15/ben-lorica-2025-07-15)_

**2. Superposition Meets Production—A Guide for AI Engineers**
_Date:_ July 17, 2025
_Key Finding:_ This newsletter delves into the current landscape and future prospects of quantum computing for AI applications, featuring insights from DeepMind veteran Jennifer Prendki. It highlights that while universal quantum computers are still some years away, specific quantum applications for machine learning are emerging today, particularly in recommendation systems, financial applications (e.g., fraud detection), and pharmaceuticals. A significant challenge is the lack of a mature "QMLOps" software layer, as the quantum computing stack is fragmented and primitive compared to classical ML infrastructure. The "no-cloning theorem" fundamentally alters data operations in quantum environments, requiring a shift to on-demand regeneration of quantum states rather than traditional backups or reproducibility. The newsletter also discusses how quantum computing enables new paradigms like Topological Data Analysis and emphasizes the need for "bridge talent" in engineering rather than deep quantum physics expertise for practitioners.
_Read more of the article: [Superposition Meets Production—A Guide for AI Engineers](https://substack.substack.com/app-link/post?publication_id=20983&post_id=167287075&utm_source=post-email-title&utm_campaign=email-post-title&isFreemail=true&r=5s83oz&token=eyJ1c2VyX2lkIjozNDk3MzgxNjMsInBvc3RfaWQiOjE2NzI4NzA3NSwiaWF0IjoxNzUyNzYxNjAwLCJleHAiOjE3NTUzNTM2MDAsImlzcyI6InB1Yi0yMDk4MyIsInN1YiI6InBvc3QtcmVhY3Rpb24ifQ.Ww9oOjjJfJeXHNyFZ8TEN2d7rOXvzD4l0xYbdDwJHCw)_
_Read more of the newsletter: [Ben Lorica - 2025/07/17](https://polskitran.github.io/Sumitup-quartz-dev/2025-07-17/ben-lorica-2025-07-17)_
"""

    # First call - should hit the API
    print("Making call...")

    def main():
        # response = call_llm(test_prompt)
        # print(response)
        audio_data = text_to_speech(newsletter_response)
        wave_file("misc/tts_test.wav", audio_data)
        print("Audio saved to tts_test.wav")

    main()
