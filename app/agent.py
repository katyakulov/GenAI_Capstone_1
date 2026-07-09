import json
import logging
import os
from typing import Any

from openai import OpenAI

from .db import run_safe_query, table_schema
from .tickets import create_github_issue, create_local_ticket

LOGGER = logging.getLogger('data-insights-app')

SYSTEM_PROMPT = """
You are a careful business data insights agent.
You help users answer questions about a SQLite business database.
Never claim that you saw the whole database. Use tools to retrieve only needed aggregated or limited data.
Do not perform destructive actions. If a user asks to delete, update, drop, alter, truncate, or overwrite data, refuse and explain that the app is read-only for safety.
When a question requires human follow-up, missing data, system access, complaint handling, or operational intervention, suggest creating a support ticket.
Keep answers concise and include the SQL logic in plain English when helpful.
"""

TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'get_database_schema',
            'description': 'Return the safe readable database schema.',
            'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'run_safe_sql_query',
            'description': 'Run a read-only SELECT query against the database. Destructive operations are blocked.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'sql': {'type': 'string', 'description': 'A single SELECT statement only.'},
                    'limit': {'type': 'integer', 'minimum': 1, 'maximum': 200, 'default': 50},
                },
                'required': ['sql'],
                'additionalProperties': False,
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'create_support_ticket',
            'description': 'Create a support ticket locally or in GitHub if configured.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'description': {'type': 'string'},
                    'priority': {'type': 'string', 'enum': ['low', 'medium', 'high', 'urgent'], 'default': 'medium'},
                },
                'required': ['title', 'description'],
                'additionalProperties': False,
            },
        },
    },
]


def _execute_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    LOGGER.info('Tool call requested: %s args=%s', name, args)
    try:
        if name == 'get_database_schema':
            return {'schema': table_schema()}
        if name == 'run_safe_sql_query':
            return {'rows': run_safe_query(args['sql'], args.get('limit', 50))}
        if name == 'create_support_ticket':
            try:
                result = create_github_issue(args['title'], args['description'], 'support')
            except Exception as exc:
                LOGGER.exception('GitHub issue creation failed; creating local ticket. Error: %s', exc)
                result = create_local_ticket(args['title'], args['description'], args.get('priority', 'medium'))
            return result
        return {'error': f'Unknown tool: {name}'}
    except Exception as exc:
        LOGGER.exception('Tool call failed')
        return {'error': str(exc)}


def answer_user(messages: list[dict[str, str]], model: str = 'gpt-4o-mini') -> str:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    api_messages = [{'role': 'system', 'content': SYSTEM_PROMPT}] + messages

    for _ in range(5):
        response = client.chat.completions.create(
            model=model,
            messages=api_messages,
            tools=TOOLS,
            tool_choice='auto',
            temperature=0.2,
        )
        msg = response.choices[0].message
        api_messages.append(msg)

        if not msg.tool_calls:
            LOGGER.info('Final assistant response produced.')
            return msg.content or ''

        for call in msg.tool_calls:
            args = json.loads(call.function.arguments or '{}')
            output = _execute_tool(call.function.name, args)
            api_messages.append({
                'role': 'tool',
                'tool_call_id': call.id,
                'name': call.function.name,
                'content': json.dumps(output, ensure_ascii=False),
            })

    LOGGER.warning('Tool loop limit reached.')
    return 'I could not complete the request within the tool-call limit. Please narrow the question or create a support ticket.'
