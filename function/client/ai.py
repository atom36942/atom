def func_client_read_gemini(*, config_gemini_key: str) -> any:
    """Initialize Gemini (Generative AI) client with the provided API key."""
    import google.generativeai as genai
    genai.configure(api_key=config_gemini_key)
    return genai

def func_client_read_openai(*, config_openai_key: str) -> any:
    """Initialize OpenAI client with the provided API key."""
    import openai
    return openai.OpenAI(api_key=config_openai_key)
