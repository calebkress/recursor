# Recursor

**Recursor** is a CLI-first lead enrichment and scoring engine. It combines AI synthesis, structured prompts, and modular research pipelines to surface and prioritize high-fit outbound targets — faster.

> Designed for use at Recurly (subscription billing platform), but easily adapted to any GTM motion.

---

## Why Recursor?

Manual research is slow. Spray-and-pray sucks.

Recursor bridges the gap — automatically enriching leads with relevant context (hiring signals, tech stack, press mentions) and scoring them via structured GPT prompts to flag the highest-potential targets.

It’s:
- **Repeatable** – CLI and prompt-based, not vibes
- **Auditable** – every score has a justification
- **Modular** – each piece (enrichment, scoring, prompts) can be swapped out
- **Personally owned** – no vendor lock-in, no guesswork

---

## Project Structure

```bash
recursor/
├── cli.py             # Main entrypoint (enrich, score, or full pipeline)
├── dashboard.py       # Optional Streamlit UI for non-technical demoing
├── enrich/            # Web enrichment modules (SerpAPI, hiring, tech stack)
├── score/             # GPT scoring logic, validation, and prompt injection
├── prompts/           # ICP-specific templates (Jinja2-style .txt files)
├── data/              # Input/output CSVs and JSON
├── config/            # API keys, model defaults, prompt metadata
├── tests/             # Unit tests for core logic
└── README.md
```

---

## Setup

```bash
# Clone and install dependencies
git clone https://github.com/yourusername/recursor.git
cd recursor
pip install -r requirements.txt

# Add your keys (SerpAPI, OpenAI)
cp config/settings.example.py config/settings.py
```

---

## Usage

### Enrich Leads from CSV

```bash
python cli.py enrich --input data/leads.csv --output data/enriched.json
```

This pulls snippets for each company using SerpAPI:
- “{{company}} hiring project manager”
- “{{company}} infrastructure news”
- “{{company}} tech stack”

---

### Score Leads with GPT

```bash
python cli.py score --input data/enriched.json --output data/scored.json
```

Each enriched lead is scored via structured GPT prompts, returning:

```json
{
  "company": "Acme Inc",
  "score": 87,
  "summary": ["Hiring PMs for new product launch", "Backend infra team scaling"],
  "justification": "Strong ICP alignment based on hiring and product activity"
}
```

---

### Full Pipeline

```bash
python cli.py full-run --input data/leads.csv --output data/scored.json
```

---

## Optional: Streamlit Dashboard

```bash
streamlit run dashboard.py
```

Upload a scored JSON file and visually sort by score, justification, or summary insight.

---

## Prompt Strategy

Prompts live in `/prompts` as `.txt` templates, with Jinja2-style variables like `{{ company }}` and `{{ enriched_snippets }}`.

Example:

```
You are scoring {{ company }} for fit with Recurly.
Here's what we know:
{{ enriched_snippets }}

Return a JSON object with "summary", "score" (0-100), and "justification".
```

---

## Future Plans

- [ ] Model fallback and retry logic
- [ ] Prompt versioning and A/B test mode
- [ ] Lead clustering (segment by justification themes)
- [ ] SDR metrics overlay (contacted, replied, converted)

---

## License

MIT License

---

## Built by Caleb Kress
