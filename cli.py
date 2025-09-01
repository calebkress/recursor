# cli.py
import argparse
from enrich.mock_enricher import enrich_companies
from score.scorer import score_companies
import json
import csv

def load_companies_from_csv(path):
    with open(path, newline='') as f:
        return [row['company'] for row in csv.DictReader(f)]

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Recurser CLI")
    parser.add_argument('--input', required=True, help='Input CSV path with "company" column')
    parser.add_argument('--output', required=True, help='Output JSON file')
    parser.add_argument('--model', default='gpt-4', help='OpenAI model (default: gpt-4)')
    parser.add_argument('--full-run', action='store_true', help='Run enrich + score pipeline')
    args = parser.parse_args()

    companies = load_companies_from_csv(args.input)
    enriched = enrich_companies(companies)
    results = score_companies(enriched, model=args.model)
    save_json(args.output, results)

if __name__ == '__main__':
    main()
