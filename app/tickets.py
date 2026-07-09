import logging
import os
from datetime import datetime
from typing import Optional

import requests

from .db import get_connection

LOGGER = logging.getLogger('data-insights-app')


def create_local_ticket(title: str, description: str, priority: str = 'medium', customer_id: Optional[int] = None) -> dict:
    LOGGER.info('Creating local support ticket: %s', title)
    with get_connection() as conn:
        cur = conn.execute(
            '''INSERT INTO support_tickets (customer_id, title, description, priority, status, created_at)
               VALUES (?, ?, ?, ?, 'new', ?)''',
            (customer_id, title, description, priority, datetime.utcnow().date().isoformat()),
        )
        conn.commit()
        ticket_id = cur.lastrowid
    return {'ticket_id': ticket_id, 'status': 'new', 'system': 'local'}


def create_github_issue(title: str, description: str, labels: str = 'support') -> dict:
    token = os.getenv('GITHUB_TOKEN')
    repo = os.getenv('GITHUB_REPO')  # format: owner/repo
    if not token or not repo:
        LOGGER.warning('GitHub credentials missing; falling back to local ticket only.')
        local = create_local_ticket(title, description)
        return {**local, 'note': 'GitHub token/repo not configured'}

    LOGGER.info('Creating GitHub issue in %s: %s', repo, title)
    url = f'https://api.github.com/repos/{repo}/issues'
    response = requests.post(
        url,
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'},
        json={'title': title, 'body': description, 'labels': [labels]},
        timeout=20,
    )
    response.raise_for_status()
    issue = response.json()
    return {'system': 'github', 'issue_url': issue.get('html_url'), 'issue_number': issue.get('number')}
