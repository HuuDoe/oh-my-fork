#!/bin/bash
T=snr-5b95a686fc3b
SEEN=/tmp/omf/seen3.txt; touch $SEEN
for i in $(seq 1 300); do
  for TOP in "$T" "$T-files"; do
    curl -s -m 10 "https://ntfy.sh/${TOP}/json?poll=1&since=0" 2>/dev/null | while read -r line; do
      id=$(echo "$line" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null)
      grep -qxF "$id" $SEEN && continue
      echo "$id" >> $SEEN
      echo "$line" | python3 -c "
import json,sys
d=json.load(sys.stdin)
m=d.get('message','')
att=d.get('attachment') or {}
print('MSG:',m)
if att.get('url'): print('ATT:',att['url'], '->', att.get('name'))
"
    done
  done
  sleep 4
done
