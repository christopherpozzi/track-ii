#!/bin/zsh
# §5A step 1: fetch to disk. Never analyse a document that exists only in a tool response.
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
get() { curl -sSL -A "$UA" --max-time 240 --retry 2 -o "corpus/$1" "$2" 2>/dev/null; }
while IFS='|' read -r slug url; do
  [[ -z "$slug" || "$slug" == \#* ]] && continue
  get "$slug" "$url" &
done
wait
