# score/scorer.py
import openai
from config.settings import OPENAI_API_KEY
import json

openai.api_key = OPENAI_API_KEY

TEMPLATE = """You are scoring {{company}} for fit with Recurly.

Here’s what we know:
{{snippet_block}}

Return a JSON object with:
- summary (3 bullets)
- score (0-100)
- justification (1 sentence)
"""

def score_companies(enriched_data, model="gpt-4"):
    results = []
    for item in enriched_data:
        company = item['company']
        snippets = "\n".join(f"- {s}" for s in item['snippets'])
        prompt = TEMPLATE.replace("{{company}}", company).replace("{{snippet_block}}", snippets)

        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            output = response['choices'][0]['message']['content']
            parsed = json.loads(output)
        except Exception as e:
            parsed = {
                "score": 0,
                "summary": ["Error scoring company"],
                "justification": str(e)
            }

        results.append({
            "company": company,
            **parsed
        })

    return results
