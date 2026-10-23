"""Scoped text-input checks on an already selected Playwright page.

Optional browser capability, not registered as an unattended agent action.
The caller owns URL authorization, isolation and execution/evidence scope.
"""
from datetime import datetime, timezone


def inspect_input_fields(page, limit=50):
    """Read DOM properties; site-specific IDs/selectors are not required."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Field inspection limit must be 1-100.')
    return page.locator('input').evaluate_all('''(elements, limit) => elements.slice(0, limit).map(e => ({
        type: e.type, id: e.id, name: e.name, placeholder: e.placeholder,
        label: Array.from(e.labels || []).map(l => l.innerText).join(' '),
        disabled: e.disabled, readOnly: e.readOnly, visible: !!e.getClientRects().length
    }))''', limit)


def _snapshot(field):
    value = field.evaluate('''e => ({tag:e.tagName, type:e.type, value:e.value,
        placeholder:e.placeholder, placeholder_shown:e.matches(':placeholder-shown'),
        disabled:e.disabled, readOnly:e.readOnly, visible:!!e.getClientRects().length})''')
    value['observed_at'] = datetime.now(timezone.utc).isoformat()
    return value


def check_text_entry(page, *, by, target, value, capture=None):
    """Check only one unambiguous ordinary text input; never click/submit a form.

    Field discovery does not supply business expectations. The caller must
    provide selected test data and a requirement-backed entry/clear intent.
    """
    if by not in {'label', 'placeholder', 'role'}:
        raise ValueError('Choose label, placeholder or role-name targeting.')
    if not isinstance(target, str) or not target.strip() or len(target) > 300:
        raise ValueError('A bounded field description is required.')
    if not isinstance(value, str) or not value or len(value) > 500:
        raise ValueError('A bounded nonempty test value is required.')
    if by == 'label':
        field = page.get_by_label(target, exact=True)
    elif by == 'role':
        field = page.get_by_role('textbox', name=target, exact=True)
    else:
        field = page.get_by_placeholder(target, exact=True)
    if field.count() != 1:
        raise ValueError('Field target must identify exactly one element; inspect labels or narrow its scope.')
    before = _snapshot(field)
    if (before['tag'] != 'INPUT' or before['type'] != 'text' or not before['visible']
            or before['disabled'] or before['readOnly'] or not field.is_editable()):
        raise ValueError('This check supports only a visible editable ordinary text input.')
    original_value = before['value']
    field.click()  # Respect pointer actionability; do not bypass overlays by filling directly.
    field.fill('')
    initial = _snapshot(field)
    if capture: capture('initial')
    field.fill(value)
    entered = _snapshot(field)
    if capture: capture('entered')
    field.press('ControlOrMeta+A')
    field.press('Backspace')
    cleared = _snapshot(field)
    if capture: capture('cleared')
    checks = {'initial_empty': initial['value'] == '',
              'exact_value_retained': entered['value'] == value,
              'select_all_backspace_cleared': cleared['value'] == ''}
    return {'by': by, 'target': target, 'test_value': value, 'original_value': original_value,
            'checks': checks, 'status': 'passed' if all(checks.values()) else 'failed',
            'observations': [initial, entered, cleared],
            'placeholder_checks': {
                'hidden_after_typing': not entered['placeholder_shown'] if entered['placeholder'] else None,
                'shown_after_clearing': cleared['placeholder_shown'] if cleared['placeholder'] else None},
            'form_submitted': False,
            'scope': 'One selected text entry/clear check; no other elements or business rules are certified.'}
