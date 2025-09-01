# enrich/mock_enricher.py
def enrich_companies(company_list):
    enriched = []
    for company in company_list:
        enriched.append({
            'company': company,
            'snippets': [
                f"{company} is hiring backend engineers",
                f"{company} recently announced a new infrastructure initiative"
            ]
        })
    return enriched
