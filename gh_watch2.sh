#!/bin/bash
SEEN=/tmp/omf/gh_seen2.txt; touch $SEEN
for i in $(seq 1 400); do
  gh api "repos/HuuDoe/oh-my-fork/commits/f29bf9fa7fab75c14497b26a459a4d6285d56483/comments" 2>/dev/null > /tmp/omf/cc2.json
  python3 - <<'PYEOF'
import json
try: cs = json.load(open('/tmp/omf/cc2.json'))
except: raise SystemExit
seen = set(l.strip() for l in open('/tmp/omf/gh_seen2.txt'))
for c in cs:
    key = c['id']
    if str(key) in seen: continue
    seen.add(str(key)); print(str(key), file=open('/tmp/omf/gh_seen2.txt','a'))
    b = c['body']
    if b.startswith('REQ '):
        import base64
        rnd = b.split()[1]
        b64 = "".join(b.split('B64:')[1].split()) if 'B64:' in b else ''
        if b64:
            open(f'/tmp/omf/req_{rnd}.mp3','wb').write(base64.b64decode(b64))
            print(f'COMMENT: {b.splitlines()[0]} b64len={len(b64)} -> /tmp/omf/req_{rnd}.mp3')
        else:
            print(f'COMMENT: {b[:80]} EMPTY-B64')
    else:
        print('COMMENT:', b[:90])
PYEOF
  sleep 6
done
