"""Fetch the Central Elections Committee turnout files and rebuild index.html.

Run from anywhere. Tracks a small turnout timeline in data/timeline.json.
Exits without touching tracked files when the downloaded bytes have not changed.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parties

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'raw'
LATEST = RAW / 'latest'
DATA = ROOT / 'data'
BASE = 'https://mapvotes.bechirot.gov.il/data/votes/'
MAP_HOME = 'https://mapvotes.bechirot.gov.il/'
JERUSALEM = ZoneInfo('Asia/Jerusalem')
MAX_BYTES = 80_000_000

REQUIRED = (
    'municipal_data.json',
    'neighborhood_data.json',
    'kalpi_data.json',
    'municipal_geometry.topojson',
    'neighborhood_geometry.topojson',
)
EXTRA = (
    'results_data.json',
    'results.json',
    'parties_data.json',
    'party_data.json',
    'national_data.json',
    'totals_data.json',
    'count_data.json',
    'votes_data.json',
    'final_data.json',
    'summary_data.json',
    'mandates_data.json',
    'seats_data.json',
    'kalpi_results_data.json',
    'municipal_results_data.json',
    'neighborhood_results_data.json',
    'ballot_results_data.json',
)


def log(message):
    print(message, flush=True)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as handle:
            handle.write(message + '\n')


def set_output(changed):
    path = os.environ.get('GITHUB_OUTPUT')
    if not path:
        return
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write(f'changed={"true" if changed else "false"}\n')


def fetch(url):
    """Download with curl. urllib from GitHub-hosted runners gets a bare 403."""
    last = None
    for attempt in range(3):
        with tempfile.NamedTemporaryFile() as handle:
            header_path = handle.name + '.hdr'
            try:
                result = subprocess.run(
                    [
                        'curl', '-sS', '-L', '--http1.1', '--compressed',
                        '--max-time', '180',
                        '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                        '-H', 'Accept: application/json,text/plain,*/*',
                        '-H', 'Accept-Language: he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
                        '-H', 'Referer: https://mapvotes.bechirot.gov.il/',
                        '-D', header_path,
                        '-o', handle.name,
                        '-w', '%{http_code}',
                        url,
                    ],
                    check=False, capture_output=True, text=True,
                )
            except Exception as error:
                last = error
                time.sleep(2 * (attempt + 1))
                continue
            status = int(result.stdout.strip() or '0')
            body = Path(handle.name).read_bytes()
            if status == 200 and body:
                if len(body) > MAX_BYTES:
                    raise RuntimeError(f'{url} is larger than {MAX_BYTES} bytes')
                return status, body
            snippet = body[:300].decode('utf-8', 'replace').replace('\n', ' ')
            log(f'fetch HTTP {status} {url} {snippet}')
            if status in (403, 404):
                return status, b''
            last = RuntimeError(result.stderr.strip() or f'HTTP {status}')
            time.sleep(2 * (attempt + 1))
    raise last


def layers_from_map():
    """Layer names the official map bundle asks for. Best effort."""
    layers = set()
    try:
        status, html = fetch(MAP_HOME)
        if status != 200:
            log(f'schema map homepage HTTP {status}')
            return layers
        text = html.decode('utf-8', 'replace')
        import re
        sources = re.findall(r'/assets/index-[^"\']+\.js', text)
        for source in sources[:2]:
            status, js = fetch(MAP_HOME.rstrip('/') + source)
            if status != 200:
                continue
            script = js.decode('utf-8', 'replace')
            layers.update(re.findall(r'fetchTurnoutFile\([^,]+,\s*"([A-Za-z0-9_]+)"\)', script))
            layers.update(re.findall(r'dataUrl\([^,]+,\s*"([A-Za-z0-9_]+)"\)', script))
            if 'fetchKalpiFile' in script:
                layers.add('kalpi')
            layers.update(re.findall(r'/([A-Za-z0-9_]+)_data\.json', script))
            layers.update(re.findall(r'/latest/([A-Za-z0-9_.-]+\.(?:json|topojson))', script))
    except Exception as error:
        log(f'schema map scan failed: {error}')
    return layers


def wanted_names(election_path):
    names = []
    for name in list(REQUIRED) + list(EXTRA):
        names.append(f'{election_path}/{name}')
    for layer in sorted(layers_from_map()):
        if layer.endswith('.json') or layer.endswith('.topojson'):
            names.append(f'{election_path}/{layer}')
        else:
            names.append(f'{election_path}/{layer}_data.json')
            names.append(f'{election_path}/{layer}_geometry.topojson')
    # Preserve order, drop duplicates.
    seen = set()
    ordered = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def schema_fields(obj):
    fields = set()
    if not isinstance(obj, dict):
        return fields
    if isinstance(obj.get('features'), dict) and isinstance(obj.get('total'), dict):
        fields.update(obj.keys())
        fields.update(f'total.{key}' for key in obj['total'])
        nested = set()
        for feature in obj['features'].values():
            if not isinstance(feature, dict):
                continue
            for key, value in feature.items():
                fields.add(f'features.*.{key}')
                if isinstance(value, dict):
                    nested.update(f'features.*.{key}.{sub}' for sub in value.keys())
        fields.update(nested)
        return fields

    def walk(node, prefix, depth):
        if not isinstance(node, dict) or depth > 4:
            return
        for key, value in node.items():
            path = f'{prefix}.{key}' if prefix else str(key)
            fields.add(path)
            if isinstance(value, dict) and len(value) <= 80:
                walk(value, path, depth + 1)
            elif isinstance(value, dict):
                fields.update(f'{path}.{sub}' for sub in value.keys())
    walk(obj, '', 0)
    return fields


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def snapshot_id(moment):
    return moment.strftime('%Y%m%d_%H%M')


def same_drop(point, source, source_time, percent, voters):
    return (
        point.get('source') == source
        and point.get('source_time') == source_time
        and point.get('percent') == percent
        and point.get('voters') == voters
    )


def main():
    os.chdir(ROOT)
    now = datetime.now(JERUSALEM)
    status, elections_body = fetch(BASE + 'elections.json?v=' + str(int(time.time())))
    if status != 200 or not elections_body:
        raise SystemExit(f'elections.json HTTP {status}')
    files = {'elections.json': elections_body}
    catalog = json.loads(elections_body)
    current = None
    for key, entry in catalog.get('elections', {}).items():
        if entry.get('isCurrent'):
            current = entry
            log(f"current election {key} path={entry.get('path')} title={entry.get('title')}")
            break
    if current is None:
        raise SystemExit('elections.json has no current election')
    election_path = current['path']
    party_names = {letter: info.get('name', letter) for letter, info in (current.get('parties') or {}).items()}

    unpublished = []
    for relative in wanted_names(election_path):
        status, body = fetch(BASE + relative + '?v=' + str(int(time.time())))
        if status == 200 and body:
            files[relative] = body
            log(f'fetched {relative} ({len(body)} bytes)')
        elif any(relative.endswith('/' + name) for name in REQUIRED):
            raise SystemExit(f'required file {relative} HTTP {status}')
        else:
            unpublished.append(f'{relative} HTTP {status}')
    if unpublished:
        log(f'{len(unpublished)} optional files are not published yet')

    digest_lines = []
    file_info = {}
    for relative in sorted(files):
        digest = hashlib.sha256(files[relative]).hexdigest()
        file_info[relative] = {'sha256': digest, 'bytes': len(files[relative])}
        digest_lines.append(f'{relative}\n{digest}\n')
    overall = hashlib.sha256(''.join(digest_lines).encode('utf-8')).hexdigest()

    state_path = DATA / 'source_state.json'
    previous = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    manifest_path = DATA / 'schema_manifest.json'
    if previous.get('sha256') == overall:
        log(f'unchanged {overall[:12]} source={previous.get("source")} {previous.get("source_time")} {previous.get("percent")}%')
        log('no schema changes')
        log('no party vote totals to add (source unchanged)')
        set_output(False)
        return

    # Persist the downloads only after we know this run will rebuild.
    LATEST.mkdir(parents=True, exist_ok=True)
    for relative, body in files.items():
        target = RAW / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)

    parsed = {}
    for relative, body in files.items():
        if relative.endswith('.json'):
            try:
                parsed[relative] = json.loads(body)
            except json.JSONDecodeError:
                log(f'SCHEMA {relative} is not JSON')

    current_fields = {name: sorted(schema_fields(doc)) for name, doc in parsed.items()}
    downloaded = set(files)
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding='utf-8'))
        old_files = set(old.get('files', []))
        old_fields = old.get('fields', {})
        for name in sorted(downloaded - old_files):
            log(f'SCHEMA new file: {name} fields={current_fields.get(name, [])[:40]}')
        for name in sorted(old_files - downloaded):
            log(f'SCHEMA file no longer published: {name}')
        for name, fields in current_fields.items():
            added = sorted(set(fields) - set(old_fields.get(name, [])))
            if added and name in old_files:
                log(f'SCHEMA new fields in {name}: {added[:40]}')
        if downloaded == old_files and all(set(current_fields[n]) == set(old_fields.get(n, [])) for n in current_fields):
            log('no new files or fields')
    else:
        log('schema baseline recorded for ' + ', '.join(sorted(downloaded)))

    documents = [(name, doc) for name, doc in parsed.items() if 'geometry' not in name]
    live, notes = parties.find_national_party_votes(documents, party_names)
    for note in notes:
        log('PARTIES ' + note)
    party_path = LATEST / 'party_national.json'
    if live:
        write_json(party_path, live)
        log(f"PARTIES rendering {len(live['parties'])} lists, {live['valid_votes']} valid votes, seats {live['seats_total']}")
    elif party_path.exists():
        party_path.unlink()

    municipal = parsed[f'{election_path}/municipal_data.json']
    timeline = rebuild_timeline(municipal, now)
    write_json(DATA / 'timeline.json', timeline)

    for script in ('build.py', 'page_data.py', 'build_site.py'):
        subprocess.check_call([sys.executable, str(ROOT / 'scripts' / script)])

    index = (ROOT / 'index.html').read_text(encoding='utf-8')
    if 'עודכן לאחרונה' not in index or '__UPDATED__' in index or '<!--__LIVE_SECTION__-->' in index:
        raise SystemExit('index.html was not rendered from the template')

    state = {
        'sha256': overall,
        'fetched_at': now.isoformat(),
        'source': municipal.get('source'),
        'source_time': municipal.get('time'),
        'percent': municipal.get('total', {}).get('percent'),
        'voters': municipal.get('total', {}).get('מצביעים'),
        'files': file_info,
    }
    write_json(state_path, state)
    write_json(manifest_path, {'files': sorted(downloaded), 'fields': current_fields})
    message = (
        f"Update turnout from the Central Elections Committee\n\n"
        f"{municipal.get('source')} at {municipal.get('time')}: "
        f"{municipal.get('total', {}).get('percent')}% "
        f"({municipal.get('total', {}).get('מצביעים')} voters).\n"
    )
    Path('/tmp/commitmsg.txt').write_text(message, encoding='utf-8')
    log(message.strip())
    set_output(True)


def rebuild_timeline(municipal, now):
    path = DATA / 'timeline.json'
    timeline = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    total = municipal['total']
    if not timeline and municipal.get('previous') and total.get('prev_percent') is not None:
        generated = datetime.fromisoformat(municipal['generated']).astimezone(JERUSALEM)
        prev = municipal['previous']
        hour, minute = prev['time'].split(':')[:2]
        timeline.append({
            'id': generated.strftime('%Y%m%d') + f'_{hour}{minute}',
            'israel_time': generated.strftime('%d.%m.%Y') + f' {hour}:{minute}',
            'source': prev.get('source'),
            'source_time': prev.get('time'),
            'percent': total.get('prev_percent'),
            'voters': total.get('prev_voters'),
            'eligible': None,
            'kalpis': None,
            'generated': None,
            'fetched_at': None,
            'kind': 'previous',
        })
    source = municipal.get('source')
    source_time = municipal.get('time')
    percent = total.get('percent')
    voters = total.get('מצביעים')
    if timeline and same_drop(timeline[-1], source, source_time, percent, voters):
        return timeline
    point = {
        'id': snapshot_id(now),
        'israel_time': now.strftime('%d.%m.%Y %H:%M'),
        'source': source,
        'source_time': source_time,
        'percent': percent,
        'voters': voters,
        'eligible': total.get('בזב'),
        'kalpis': total.get('kalpis'),
        'generated': municipal.get('generated'),
        'fetched_at': now.astimezone(ZoneInfo('UTC')).isoformat(),
        'kind': 'drop',
    }
    if timeline and timeline[-1].get('id') == point['id'] and timeline[-1].get('kind') != 'previous':
        timeline[-1] = point
    else:
        timeline.append(point)
    return timeline


if __name__ == '__main__':
    main()
