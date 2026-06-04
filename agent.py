import os
import time

from google import genai
from google.genai import types


PRIMARY_MODEL = "gemini-2.5-pro"
FALLBACK_MODEL = "gemini-2.5-flash"


def generate_company_report(company_name: str) -> str:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable not found."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a Principal AI Engineer and Business Strategist.

Perform a deep factual company intelligence assessment on:

{company_name}

Your response MUST contain:

# Company Overview
# Key Business Information
# Business Challenges
# Company-Specific AI Opportunities
# Personalized CEO Pitch
"""

    models_to_try = [
        PRIMARY_MODEL,
        FALLBACK_MODEL,
    ]

    last_error = None

    for model_name in models_to_try:

        try:

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    tools=[{"google_search": {}}],
                ),
            )

            return response.text

        except Exception as e:

            last_error = str(e)

            if "RESOURCE_EXHAUSTED" in last_error:
                time.sleep(5)
                continue

            raise

    raise RuntimeError(
        f"All Gemini models failed.\n\nLast Error:\n{last_error}"
    )