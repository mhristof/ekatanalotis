#!/bin/bash
# Commit what changed under the given paths and push it to main, replaying
# the commit on top of main if another job pushed in the meantime.
#
# usage: commit_push.sh <message> <path>...

set -euo pipefail

message=$1
shift
remote=${REMOTE:-origin}

git add --sparse "$@"

if git diff --cached --quiet; then
    echo "no changes to commit"
    exit 0
fi

git commit -q -m "$message"

for _ in 1 2 3 4 5; do
    git push -q "$remote" HEAD:main && exit 0
    git fetch -q --depth=1 "$remote" main
    git rebase -q --onto FETCH_HEAD HEAD~1
done

exit 1
