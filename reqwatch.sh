#!/bin/bash
KEY=""
for i in $(seq 1 100); do
  [ -z "$KEY" ] && KEY=$(curl -s -m 8 https://paste.rs/snans-key 2>/dev/null | tr -d ' \n')
  [ -z "$KEY" ] && { sleep 8; continue; }
  for r in $(seq 0 13); do
    f="/tmp/omf/req_${KEY}_${r}"
    [ -f "$f" ] && continue
    u=$(curl -s -m 8 "https://paste.rs/${KEY}-req${r}" 2>/dev/null | tr -d ' \n')
    if [[ "$u" == http* ]]; then
      echo "$u" > "$f"
      curl -sL -m 30 "$u" -o "/tmp/omf/hitl_${KEY}_${r}.mp3" 2>/dev/null
      echo "REQ_${r}: ${u} -> /tmp/omf/hitl_${KEY}_${r}.mp3"
    fi
  done
  sleep 8
done
