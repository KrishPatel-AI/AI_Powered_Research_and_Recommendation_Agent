import os
import time

from google import genai
from google.genai import types


PRIMARY_MODEL = "gemini-2.5-pro"
FALLBACK_MODEL = "gemini-2.5-flash"

# Exact section headers the app.py parser will look for
REQUIRED_SECTIONS = [
    "Company Overview",
    "Key Business Information",
    "Business Challenges",
    "Company-Specific AI Opportunities",
    "Personalized CEO Pitch",
]


def generate_company_report(company_name: str) -> str:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not found.")

    client = genai.Client(api_key=api_key)

    # Strict prompt: no preamble, exact H1 headers, consistent structure
    prompt = f"""You are a Principal AI Engineer and Business Strategist with deep expertise in enterprise research.

Perform a comprehensive, factual intelligence assessment on the company: **{company_name}**

STRICT FORMATTING RULES — follow these exactly:
1. Start your response DIRECTLY with the first section header. Do NOT write any introduction, greeting, or preamble before the first section.
2. Use EXACTLY these five section headers (H1 markdown, single #):

# Company Overview
# Key Business Information
# Business Challenges
# Company-Specific AI Opportunities
# Personalized CEO Pitch

3. Under each H1 section, use ## for sub-sections and ### for sub-sub-sections only.
4. Do NOT add any section beyond the five listed above.
5. Do NOT add any concluding paragraph after the last section.

---

CONTENT REQUIREMENTS:

# Company Overview
- What the company does (core business model)
- Industry and market segment
- Scale (revenue range, employee count, project count if applicable)
- Geographic presence and key markets
- Founded year and key milestones

# Key Business Information
- Major products / service offerings (be specific)
- Recent developments (last 12–18 months)
- Announced expansion plans or strategic initiatives
- Key leadership and ownership structure
- Important public financials or funding information

# Business Challenges
For each challenge, explain your reasoning with evidence:
- Market / competitive challenges
- Operational bottlenecks
- Sales and lead conversion challenges
- Customer experience pain points
- Regulatory or compliance challenges (if applicable)

# Company-Specific AI Opportunities
Do NOT give generic answers. Every opportunity must be specific to {company_name}'s business model and challenges.
For each opportunity, state:
- The specific problem it solves for {company_name}
- The AI/ML approach recommended
- Estimated business impact

Cover at minimum: Sales & Lead Gen, Customer Experience, Operations, Analytics, Document Processing.

# Personalized CEO Pitch
Write this as a professional one-page pitch addressed to the CEO of {company_name}.
Structure:
- Opening: Why you are reaching out specifically to them
- Observations: 3 specific things you noticed about their business
- Recommendations: 3 AI solutions tailored to their challenges
- Call to Action: Specific next step
Keep it direct, confident, and data-informed."""

    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
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

    raise RuntimeError(f"All Gemini models failed.\n\nLast Error:\n{last_error}")


def generate_competitor_snapshot(company_name: str, industry_hint: str = "") -> str:
    """Generate a brief competitor comparison table for the given company."""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not found.")

    client = genai.Client(api_key=api_key)

    prompt = f"""You are a market research analyst.

For the company **{company_name}** {f'in the {industry_hint} industry' if industry_hint else ''}, identify its top 3–4 direct competitors and produce a structured comparison.

STRICT FORMATTING RULES:
- Start DIRECTLY with the markdown table. No preamble.
- After the table, add a short "## Key Differentiators" section (3–5 bullet points) explaining what sets {company_name} apart from these competitors.
- Do NOT add any text before the table or after the Key Differentiators section.

Use this exact table format:

| Attribute | {company_name} | Competitor 1 | Competitor 2 | Competitor 3 |
|-----------|---------------|--------------|--------------|--------------|
| Founded | ... | ... | ... | ... |
| Revenue Range | ... | ... | ... | ... |
| Key Markets | ... | ... | ... | ... |
| Primary Strength | ... | ... | ... | ... |
| Biggest Weakness | ... | ... | ... | ... |
| AI Adoption Level | Low/Med/High | ... | ... | ... |

Fill in real, researched data. Use "N/A" only if genuinely unavailable."""

    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
    last_error = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
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

    raise RuntimeError(f"Competitor snapshot failed.\n\nLast Error:\n{last_error}")