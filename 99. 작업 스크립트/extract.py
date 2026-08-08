"""
MusicXML에서 프롬나드 주선율 추출 — 무소르그스키 원곡 (퍼블릭 도메인)
높은음자리표 최상성부만, 4분음표 단위 길이로.
"""
import json
import xml.etree.ElementTree as ET

STEP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
NAME = ['C', 'C#', 'D', 'E♭', 'E', 'F', 'F#', 'G', 'A♭', 'A', 'B♭', 'B']

SECTIONS = [
    ('Promenade I',        0,   23,  'B♭장조'),
    ('Promenade II',       123, 134, ''),
    ('Promenade III',      240, 246, 'B장조'),
    ('Promenade IV',       342, 350, ''),
    ('Promenade V',        420, 444, 'B♭장조'),
    ('Con mortuis (주제변형)', 516, 535, ''),
]


def midi_of(pitch):
    s = pitch.findtext('step')
    o = int(pitch.findtext('octave'))
    al = pitch.findtext('alter')
    a = int(float(al)) if al else 0
    return 12 * (o + 1) + STEP[s] + a


def extract(path='score.xml'):
    root = ET.parse(path).getroot()
    part = root.findall('.//part')[0]
    measures = part.findall('measure')
    out = {}

    for label, i0, i1, keyname in SECTIONS:
        div = 480
        meta = []
        events = []          # (onset_in_quarters, midi, dur_quarters)
        tpos = 0.0
        for i in range(i0, i1 + 1):
            m = measures[i]
            d = m.find('.//divisions')
            if d is not None:
                div = int(d.text)
            tm = m.find('.//time')
            if tm is not None:
                meta.append((i - i0 + 1, '%s/%s' % (tm.findtext('beats'),
                                                    tm.findtext('beat-type'))))
            cursor = 0.0
            onsets = {}
            for n in m.findall('note'):
                staff = n.findtext('staff') or '1'
                dur = float(n.findtext('duration') or 0) / div
                is_chord = n.find('chord') is not None
                if n.find('rest') is not None:
                    if not is_chord:
                        cursor += dur
                    continue
                pit = n.find('pitch')
                if pit is None:
                    if not is_chord:
                        cursor += dur
                    continue
                at = cursor if not is_chord else cursor - 0  # 화음은 같은 시점
                if is_chord:
                    at = onsets.get('last', cursor)
                if staff == '1':
                    key = round(tpos + at, 4)
                    mi = midi_of(pit)
                    if key not in events_map(events):
                        pass
                    events.append((key, mi, dur))
                if not is_chord:
                    onsets['last'] = cursor
                    cursor += dur
            # 마디 길이
            beats = 4.0
            if meta:
                b, bt = meta[-1][1].split('/')
                beats = float(b) * 4.0 / float(bt)
            tpos += beats

        # 같은 시점의 화음에서 최고음만 = 주선율
        top = {}
        for t, mi, du in events:
            if t not in top or mi > top[t][0]:
                top[t] = (mi, du)
        mel = [(t, top[t][0], top[t][1]) for t in sorted(top)]
        out[label] = {'meta': meta, 'melody': mel, 'key': keyname}
    return out


def events_map(ev):
    return {}


if __name__ == '__main__':
    res = extract()
    for label, d in res.items():
        mel = d['melody']
        print('\n' + '=' * 62)
        print('%s   %s   음 %d개' % (label, d['key'], len(mel)))
        print('박자 변화:', ' → '.join('m%d %s' % x for x in d['meta'][:8]))
        line, bar = [], []
        for t, mi, du in mel[:26]:
            bar.append('%s%d' % (NAME[mi % 12], mi // 12 - 1))
        print('앞 26음:', ' '.join(bar))
        print('MIDI  :', [m for _, m, _ in mel[:26]])
    json.dump({k: {'meta': v['meta'], 'melody': v['melody']}
               for k, v in res.items()},
              open('promenades.json', 'w'), ensure_ascii=False, indent=1)
    print('\npromenades.json 저장')
