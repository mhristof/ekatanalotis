#!/bin/bash
# Hourly run for a slow store (see slow.py), from a checkout of main:
#  1. every data/<store>-<day> branch of a previous day becomes one commit
#     on main with smdata/<store>-<day>.csv, and the branch is deleted
#  2. the next sections of today are scraped and pushed to the
#     data/<store>-<today> branch
# Exits non-zero when a section or a finished day failed.
#
# TODAY and REMOTE can be overridden for testing.

set -euo pipefail

# everything is in functions so bash has parsed the whole file before the
# day branch checkout below replaces it on disk
finalize_previous_days() {
    local ref branch day

    for ref in $(git ls-remote --heads "$remote" "data/$store-*" | awk '{print $2}'); do
        branch=${ref#refs/heads/}
        day=${branch#data/$store-}

        [[ "$day" < "$today" ]] || continue

        echo "finalizing $branch"
        git fetch -q --depth=1 "$remote" main
        git checkout -q -B main FETCH_HEAD
        git fetch -q --depth=1 "$remote" "$branch"
        git checkout -q FETCH_HEAD -- pending/
        git reset -q -- pending/

        python -u slow.py finalize "$store" "$day" || status=1
        rm -rf pending/

        REMOTE=$remote bash scripts/commit_push.sh "Update $store csv for $day" smdata/

        git push -q "$remote" --delete "$branch"
    done
}

scrape_today() {
    local branch="data/$store-$today" main

    git fetch -q --depth=1 "$remote" main
    main=$(git rev-parse FETCH_HEAD)

    if git ls-remote --exit-code --heads "$remote" "$branch" >/dev/null; then
        git fetch -q --depth=1 "$remote" "$branch"
    fi

    git checkout -q -B "$branch" FETCH_HEAD

    # the day branch was cut from main when the day started; run the code
    # of main so fixes apply the same day, only pending/ is committed below
    git checkout -q "$main" -- . ':(exclude)pending'
    git reset -q

    python -u slow.py scrape "$store" --date "$today" || status=1

    git add --sparse pending/

    if ! git diff --cached --quiet; then
        git commit -q -m "$store: $today progress"
        git push -q "$remote" "$branch"
    fi
}

main() {
    store=$1
    today=${TODAY:-$(date -u +%Y-%m-%d)}
    remote=${REMOTE:-origin}
    status=0

    finalize_previous_days
    scrape_today

    exit $status
}

main "$@"
