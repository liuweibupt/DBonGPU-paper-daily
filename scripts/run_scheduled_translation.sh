#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <remote SSH URL> <state directory>" >&2
    exit 1
fi

remote_url=$1
mkdir -p -- "$2"
state_dir=$(cd -- "$2" && pwd -P)

exec 9>"$state_dir/run.lock"
if ! flock -n 9; then
    echo 'A scheduled paper translation is already running.'
    exit 0
fi

export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND=${GIT_SSH_COMMAND:-ssh -o BatchMode=yes}

# Ignore the invoking checkout's Git context, including when run from a Git hook.
while IFS= read -r variable; do
    unset "$variable"
done < <(git rev-parse --local-env-vars)

mirror="$state_dir/repository.git"
cache_dir="$state_dir/cache"
mkdir -p -- "$cache_dir"
if [[ ! -d "$mirror" ]]; then
    git init --bare --initial-branch=main -- "$mirror"
fi

run_dir=''
cleanup() {
    if [[ -n "$run_dir" ]]; then
        git --git-dir="$mirror" worktree remove --force "$run_dir/checkout" 2>/dev/null || true
        rm -rf -- "$run_dir"
        run_dir=''
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# The bare repository belongs to this scheduler, so stale worktree metadata can be pruned.
git --git-dir="$mirror" worktree prune --expire now

for attempt in 1 2 3; do
    echo "Refreshing daily translations (attempt $attempt/3)."
    if ! git --git-dir="$mirror" fetch --no-tags -- "$remote_url" \
        +refs/heads/main:refs/remotes/origin/main; then
        continue
    fi

    run_dir=$(mktemp -d -- "$state_dir/work.XXXXXXXX")
    checkout="$run_dir/checkout"
    git --git-dir="$mirror" worktree add --detach --quiet "$checkout" refs/remotes/origin/main

    refresh_status=0
    (cd -- "$checkout" && python3 scripts/refresh_daily_translations.py --cache-dir "$cache_dir") \
        || refresh_status=$?
    if ((refresh_status != 0 && refresh_status != 2)); then
        exit "$refresh_status"
    fi

    # The Python command selects the report dates. Only stage its daily report output.
    git -C "$checkout" ls-files --modified --others --exclude-standard -z > "$run_dir/changed-files"
    while IFS= read -r -d '' report; do
        case "$report" in
            docs/index.html|docs/architecture/index.html|\
            docs/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].html|\
            docs/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json|\
            docs/architecture/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].html|\
            docs/architecture/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json)
                if [[ -f "$checkout/$report" && ! -L "$checkout/$report" ]]; then
                    git -C "$checkout" add -- "$report"
                fi
                ;;
        esac
    done < "$run_dir/changed-files"
    if git -C "$checkout" diff --cached --quiet; then
        exit "$refresh_status"
    fi

    git -C "$checkout" -c 'user.name=Paper Daily Codex' \
        -c 'user.email=paper-daily-codex@users.noreply.github.com' -c commit.gpgsign=false \
        commit -m 'docs: refresh daily paper translations with Codex'
    if git -C "$checkout" push -- "$remote_url" HEAD:refs/heads/main; then
        exit "$refresh_status"
    fi

    echo 'Push failed. A retry will refresh from the current remote main.' >&2
    cleanup
done

echo 'Daily translations could not be pushed after three attempts.' >&2
exit 1
