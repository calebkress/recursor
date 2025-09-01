# cli.py
import argparse
import csv, json
from enrich.mock_enricher import enrich_companies
from score.scorer import score_companies

def load_csv(path):
    with open(path, newline='') as f:
        return [row['company'] for row in csv.DictReader(f)]

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--model', default='gpt-4o')
    args = parser.parse_args()

    companies = load_csv(args.input)
    enriched = enrich_companies(companies)
    results = score_companies(enriched, model=args.model)
    save_json(args.output, results)

if __name__ == '__main__':
    main()
