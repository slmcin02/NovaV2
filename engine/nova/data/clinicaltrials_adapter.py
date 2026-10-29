from __future__ import annotations

from pathlib import Path
import requests


class ClinicalTrialsAdapter:
    def __init__(self, cache_dir: str | Path = 'data/raw/clinicaltrials'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def search(self, query: str, page_size: int = 10) -> list[dict]:
        try:
            r = requests.get(
                'https://clinicaltrials.gov/api/query/study_fields',
                params={
                    'expr': query,
                    'fields': 'NCTId,Condition,BriefTitle,LeadSponsorName,OverallStatus,PrimaryCompletionDate',
                    'min_rnk': 1,
                    'max_rnk': page_size,
                    'fmt': 'json',
                },
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
            return ((data.get('StudyFieldsResponse') or {}).get('StudyFields') or [])
        except Exception:
            return []
