"""Find national party vote totals in CEC JSON, and estimate Knesset seats.

The 26th-Knesset count files are not published yet. This walks whatever JSON
the committee serves and keeps a tally only when party letters map to vote
counts. Turnout files (בזב / מצביעים / percent) do not match.
"""

SEATS = 120
VOTE_KEYS = ('votes', 'קולות', 'valid', 'כשרים', 'count', 'total')


def passes_threshold(votes, total):
    """3.25% of valid votes, compared in integers (votes / total >= 325/10000)."""
    return total > 0 and votes * 10000 >= total * 325


def threshold_votes(total):
    if total <= 0:
        return 0
    return (total * 325 + 9999) // 10000


def bader_ofer(votes, seats=SEATS):
    """Bader-Ofer seat allocation, which is the D'Hondt highest-averages method.

    Lists under the threshold receive no seats. Surplus agreements
    (הסכמי עודפים) are not applied; this is an estimate from the vote totals.
    """
    clean = {p: int(v) for p, v in votes.items() if v and int(v) > 0}
    total = sum(clean.values())
    if total <= 0:
        return {}
    passed = {p: v for p, v in clean.items() if passes_threshold(v, total)}
    alloc = {p: 0 for p in clean}
    if not passed:
        return alloc
    for _ in range(seats):
        winner = max(passed, key=lambda p: (passed[p] / (alloc[p] + 1), passed[p]))
        alloc[winner] += 1
    return alloc


def _as_votes(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value >= 0 and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        for key in VOTE_KEYS:
            if key in value:
                return _as_votes(value[key])
    return None


def _tally_from_party_dict(obj, letters):
    if not isinstance(obj, dict) or not obj:
        return None
    votes = {}
    fractional = False
    for key, value in obj.items():
        if key not in letters:
            continue
        if isinstance(value, float) and not value.is_integer():
            fractional = True
        counted = _as_votes(value)
        if counted is None:
            continue
        votes[key] = counted
    if len(votes) < 2 or sum(votes.values()) <= 0:
        return None
    # Percents (27.4) are not vote counts.
    if fractional and max(votes.values()) <= 100:
        return None
    return votes


def _tally_from_records(items, letters):
    if not isinstance(items, list) or len(items) < 2 or not all(isinstance(x, dict) for x in items):
        return None
    votes = {}
    for item in items:
        letter = item.get('letter') or item.get('code') or item.get('אות') or item.get('party') or item.get('סמל')
        if letter not in letters:
            continue
        counted = None
        for key in VOTE_KEYS:
            if key in item:
                counted = _as_votes(item[key])
                break
        if counted is None:
            continue
        votes[letter] = votes.get(letter, 0) + counted
    if len(votes) < 2 or sum(votes.values()) <= 0:
        return None
    return votes


def _pattern(path):
    return '.'.join('*' if part.isdigit() else part for part in path.split('.'))


def find_national_party_votes(documents, party_names):
    """Return (tally or None, notes).

    documents: sequence of (filename, parsed_json)
    party_names: letter -> Hebrew name, from elections.json
    """
    letters = set(party_names)
    found = []

    def walk(filename, obj, path):
        if isinstance(obj, dict):
            tally = _tally_from_party_dict(obj, letters)
            if tally:
                found.append((filename, path or '$', tally))
            for key, value in obj.items():
                child = f'{path}.{key}' if path else str(key)
                if key == 'features' and isinstance(value, dict):
                    for fid, feature in value.items():
                        walk(filename, feature, f'{child}.{fid}')
                else:
                    walk(filename, value, child)
        elif isinstance(obj, list):
            tally = _tally_from_records(obj, letters)
            if tally:
                found.append((filename, path or '$', tally))
            if len(obj) <= 20000:
                for item in obj:
                    if isinstance(item, (dict, list)):
                        walk(filename, item, path + '[]' if path else '[]')

    for filename, doc in documents:
        if isinstance(doc, (dict, list)):
            walk(filename, doc, '')

    if not found:
        return None, ['no party vote totals found']

    grouped = {}
    for filename, path, tally in found:
        grouped.setdefault((filename, _pattern(path)), []).append(tally)

    options = []
    for (filename, pattern), tallies in grouped.items():
        combined = {}
        for tally in tallies:
            for letter, count in tally.items():
                combined[letter] = combined.get(letter, 0) + count
        options.append({
            'source_file': filename,
            'json_path': pattern,
            'parts': len(tallies),
            'votes': combined,
            'total': sum(combined.values()),
        })
    best = max(options, key=lambda item: (item['total'], -item['parts']))
    notes = [
        f"party votes from {best['source_file']} at {best['json_path']} "
        f"({best['parts']} object(s), {best['total']} votes)"
    ]
    return _package(best, party_names), notes


def _package(best, party_names):
    votes = best['votes']
    total = best['total']
    seats = bader_ofer(votes)
    parties = []
    for letter, count in sorted(votes.items(), key=lambda kv: (-kv[1], kv[0])):
        pct = round(count / total * 100, 2) if total else 0.0
        parties.append({
            'letter': letter,
            'name': party_names.get(letter, letter),
            'votes': count,
            'pct': pct,
            'seats': int(seats.get(letter, 0)),
            'passed': passes_threshold(count, total),
        })
    return {
        'source_file': best['source_file'],
        'json_path': best['json_path'],
        'valid_votes': total,
        'threshold_pct': 3.25,
        'threshold_votes': threshold_votes(total),
        'seat_method': 'bader-ofer',
        'seats_total': sum(p['seats'] for p in parties),
        'parties': parties,
    }
