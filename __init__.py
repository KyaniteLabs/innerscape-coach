"""Native Hermes adapter. Import and registration do not create a ledger."""
import json
from pathlib import Path
import re
import sqlite3
from .ledger import Ledger, text

SOURCE = '5412d80df6d64ca853dfb804354029a26e1df952'


def platform_name(platform=None):
    from gateway.session_context import get_session_env
    # Session-bound gateway identity takes precedence over command context.
    return get_session_env('HERMES_SESSION_PLATFORM', '') or platform or ''


def allowed(ctx, platform=None):
    return platform_name(platform) in ('cli', 'tui', 'desktop') or ctx.get_config('allow_gateway_writes', False) is True


def unstuck(task=''):
    text(task, 'task', 200, empty=True)
    source = Path(__file__).parent / 'skills/innerscape-coach/protocol.md'
    protocol = source.read_text(encoding='utf-8')
    section = protocol.split('## Task Initiation Protocol\n', 1)[1].split('\n## ', 1)[0].strip()
    return {'source': f'https://github.com/KyaniteLabs/unstuck-coach-protocol/blob/{SOURCE}/rules.md',
            'protocol_quote': section, 'next_action': 'Open the thing. That counts.',
            'target_data': task, 'check': 'Is the task surface open?',
            'limitation': 'Static first-contact coaching, not a diagnosis or a full adaptive protocol.'}


def register(ctx):
    from hermes_cli.config import get_hermes_home
    ledger = Ledger(get_hermes_home() / 'plugin-data' / 'innerscape-coach' / 'ledger.db')

    def run(name, args, platform=None):
        try:
            if not isinstance(args, dict):
                raise ValueError('arguments must be an object')
            mutating = name in ('checkin', 'goal') or (name == 'habit' and args.get('action') != 'summary')
            if mutating and not allowed(ctx, platform):
                return json.dumps({'error': 'Writes refused: nonlocal or unknown platform; explicit allow_gateway_writes=true required.'})
            if name == 'checkin':
                result = ledger.checkin(**args)
            elif name == 'goal':
                result = ledger.goal(**args)
            elif name == 'habit':
                result = ledger.habit(**args)
            elif name == 'unstuck':
                result = unstuck(**args)
            else:
                result = {'brief': ledger.brief()}
            return json.dumps({'ok': True, 'result': result})
        except (ValueError, TypeError):
            return json.dumps({'error': 'Invalid arguments or goal transition. See tool schema.'})
        except (OSError, sqlite3.Error, IndexError):
            return json.dumps({'error': 'Ledger or bundled protocol unavailable; no coaching result produced.'})

    properties = {
        'checkin': {'mood': {'type': 'integer', 'minimum': 1, 'maximum': 5}, 'energy': {'type': 'integer', 'minimum': 1, 'maximum': 5}, 'note': {'type': 'string', 'maxLength': 500}},
        'goal': {'action': {'type': 'string', 'enum': ['set', 'complete', 'abandon']}, 'title': {'type': 'string', 'maxLength': 200}, 'goal_id': {'type': 'integer', 'minimum': 1}},
        'habit': {'action': {'type': 'string', 'enum': ['mark', 'summary']}, 'name': {'type': 'string', 'maxLength': 100}},
        'unstuck': {'task': {'type': 'string', 'maxLength': 200}}, 'brief': {}}
    required = {'checkin': ['mood', 'energy'], 'goal': ['action'], 'habit': ['action']}
    for name, props in properties.items():
        def handler(args, _name=name, **kwargs):
            return run(_name, args)
        ctx.register_tool(name='coach_' + name, toolset='innerscape-coach',
                          schema={'name': 'coach_' + name, 'description': 'Profile-shared coaching ' + name,
                                  'parameters': {'type': 'object', 'properties': props, 'required': required.get(name, []), 'additionalProperties': False}}, handler=handler)

    def pre_llm_call(user_message='', **kwargs):
        if isinstance(user_message, str) and re.search(r'\b(stuck|blocked)\b|where[ -]was[ -]i', user_message[:10000], re.I):
            try:
                return {'context': ledger.brief()}
            except (OSError, sqlite3.Error):
                return {'context': 'Innerscape Coach ledger unavailable.'}

    def post_tool_call(tool_name='', status='unknown', **kwargs):
        if allowed(ctx):
            try:
                ledger.outcome(tool_name, status)
            except (OSError, sqlite3.Error):
                return None  # Optional telemetry must not break tool delivery.

    def checkin(raw_args, platform=None, **kwargs):
        try:
            if not isinstance(raw_args, str) or len(raw_args) > 600:
                raise ValueError()
            parts = raw_args.split(maxsplit=2)
            return run('checkin', {'mood': int(parts[0]), 'energy': int(parts[1]), 'note': parts[2] if len(parts) > 2 else ''}, platform)
        except (ValueError, IndexError):
            return 'Usage: /checkin <mood 1-5> <energy 1-5> [note]'

    def slash_unstuck(raw_args, **kwargs):
        return run('unstuck', {'task': raw_args})

    def review(raw_args, **kwargs):
        return run('brief', {})

    ctx.register_hook('pre_llm_call', pre_llm_call)
    ctx.register_hook('post_tool_call', post_tool_call)
    ctx.register_command('checkin', checkin, description='Record mood and energy', args_hint='<mood> <energy> [note]')
    ctx.register_command('unstuck', slash_unstuck, description='One first-contact action', args_hint='[task]')
    ctx.register_command('coach-review', review, description='Read profile-shared ledger brief')
