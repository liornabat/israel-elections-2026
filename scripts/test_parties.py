"""Checks for seat allocation and for the party-vote detector. Uses the real 2022
national totals from past/national_results.csv, not placeholder site data."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parties

ROOT = Path(__file__).resolve().parents[1]


def official_2022():
    votes = {}
    seats = {}
    with open(ROOT / 'past' / 'national_results.csv', encoding='utf-8-sig') as handle:
        for row in csv.DictReader(handle):
            if row['knesset'] != '25':
                continue
            votes[row['letter']] = int(row['votes'])
            seats[row['letter']] = int(row['seats'])
    return votes, seats


def test_bader_ofer_2022():
    votes, official = official_2022()
    # Official seats include surplus agreements. The estimate only has to be a
    # complete 120-seat allocation that keeps sub-threshold lists at zero and
    # stays close to the published Likud total.
    estimate = parties.bader_ofer(votes)
    assert sum(estimate.values()) == 120, estimate
    for letter, count in votes.items():
        if not parties.passes_threshold(count, sum(votes.values())):
            assert estimate.get(letter, 0) == 0, letter
        elif official[letter] > 0:
            assert estimate[letter] > 0, letter
    assert abs(estimate['מחל'] - official['מחל']) <= 2, (estimate['מחל'], official['מחל'])
    print('bader-ofer 2022', {k: estimate[k] for k in list(estimate)[:8]}, 'likud', estimate['מחל'], 'official', official['מחל'])


def test_detector_ignores_turnout_and_reads_counts():
    municipal = {
        'kind': 'percent',
        'total': {'kalpis': 10, 'בזב': 100, 'מצביעים': 40, 'percent': 40.0},
        'features': {'3000': {'שם ישוב': 'ירושלים', 'kalpis': 2, 'בזב': 50, 'מצביעים': 20, 'percent': 40.0}},
    }
    names = {'מחל': 'הליכוד', 'פה': 'אני ואתה', 'שס': 'ש"ס', 'ג': 'יהדות התורה'}
    found, notes = parties.find_national_party_votes([('latest/municipal_data.json', municipal)], names)
    assert found is None, found
    assert notes == ['no party vote totals found']

    national = {'מחל': 5000, 'פה': 3000, 'שס': 100, 'ג': 50}
    found, notes = parties.find_national_party_votes([('latest/results_data.json', {'total': national})], names)
    assert found['valid_votes'] == 8150
    assert found['parties'][0]['letter'] == 'מחל'
    assert found['parties'][0]['name'] == 'הליכוד'
    assert sum(p['seats'] for p in found['parties']) == 120
    assert found['parties'][-1]['passed'] is False or found['parties'][-1]['votes'] >= parties.threshold_votes(8150)

    per_place = {
        'features': {
            '1': {'votes': {'מחל': 1000, 'פה': 10, 'שס': 5}},
            '2': {'votes': {'מחל': 200, 'פה': 800, 'שס': 1}},
        }
    }
    found, _ = parties.find_national_party_votes([('latest/municipal_results_data.json', per_place)], names)
    assert found['valid_votes'] == 2016
    by_letter = {p['letter']: p['votes'] for p in found['parties']}
    assert by_letter['מחל'] == 1200
    assert by_letter['פה'] == 810

    records = [{'letter': 'מחל', 'קולות': 80}, {'letter': 'פה', 'קולות': 20}, {'letter': 'שס', 'קולות': 5}]
    found, _ = parties.find_national_party_votes([('latest/results.json', {'rows': records})], names)
    assert found['valid_votes'] == 105
    percents = {'מחל': 40.5, 'פה': 22.25}
    found, notes = parties.find_national_party_votes([('latest/x.json', percents)], names)
    assert found is None
    print('detector ok', notes)


def test_real_turnout_file_has_no_party_votes():
    path = ROOT / 'raw' / 'latest' / 'municipal_data.json'
    elections = ROOT / 'raw' / 'elections.json'
    if not path.exists() or not elections.exists():
        print('skip live turnout fixture (raw/ not downloaded)')
        return
    catalog = json.loads(elections.read_text(encoding='utf-8'))
    names = {letter: info['name'] for letter, info in catalog['elections']['26']['parties'].items()}
    doc = json.loads(path.read_text(encoding='utf-8'))
    found, notes = parties.find_national_party_votes([('latest/municipal_data.json', doc)], names)
    assert found is None, found
    print('live municipal file', notes)


if __name__ == '__main__':
    test_bader_ofer_2022()
    test_detector_ignores_turnout_and_reads_counts()
    test_real_turnout_file_has_no_party_votes()
    print('ok')
