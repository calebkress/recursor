def enrich_companies(company_list):
    return [
        {
            "company": c,
            "snippets": [
                f"{c} is hiring PMs for infra.",
                f"{c} added subscription features to their product."
            ]
        }
        for c in company_list
    ]
