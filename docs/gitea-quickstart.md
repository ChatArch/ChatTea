# ChatTea / Gitea End-to-End Quick Start

This quick start documents the ChatTea + Gitea workflow we practiced against a managed Gitea service. It uses placeholders so the committed docs do not expose real hostnames, organization names, user names, repository names, tokens, passwords, local paths, or run logs.

It assumes a Gitea service is already running and ChatTea can read its restricted local env file. For the service exposure pattern, see [ChatTea-managed Gitea Service Operations](gitea-service-operations.md). For the command map, see [ChatTea CLI Capability Map](chattea-cli-tree.md).

## Placeholder Convention

| Placeholder | Meaning |
| --- | --- |
| `<gitea-api-base-url>` | API/browser base URL used by ChatTea |
| `<gitea-public-base-url>` | Public HTTPS base URL used for browser/git access |
| `<chatarch-home>` | Local ChatArch runtime home |
| `<restricted-env-file>` | Machine-local env file that stores private service credentials |
| `<chatarch-venv>` | Python environment that provides `chattea` |
| `<demo-org>` | Example organization name |
| `<demo-user>` | Example user name |
| `<demo-repo>` | Example repository name |
| `<demo-owner>/<demo-repo>` | Example owner/repository pair |
| `<feature-branch>` | Example feature branch name |
| `<issue-number>` | Example issue number |
| `<pr-number>` | Example pull request number |
| `<comment-id>` | Example issue/PR comment id |
| `<team-id>` | Example organization team id |

## 0. Prepare The Environment

Load the restricted env on the service host:

```bash
set -a
source <restricted-env-file>
set +a

export CHATTEA=<chatarch-venv>/bin/chattea
export GITEA_API=<gitea-api-base-url>
export GITEA_PUBLIC=<gitea-public-base-url>
```

Check auth and API reachability:

```bash
$CHATTEA auth status
$CHATTEA api /version --url "$GITEA_API"
```

## 1. Create An Organization

ChatTea does not yet have a dedicated `org create` wrapper, so use raw API:

```bash
export DEMO_ORG=<demo-org>

$CHATTEA api /orgs \
  --method POST \
  --url "$GITEA_API" \
  --data '{
    "username": "<demo-org>",
    "full_name": "Demo Organization",
    "description": "Temporary organization for a quickstart run.",
    "visibility": "public"
  }'
```

Common org inspection:

```bash
$CHATTEA api /orgs/$DEMO_ORG --url "$GITEA_API"
$CHATTEA api /orgs/$DEMO_ORG/teams --url "$GITEA_API"
```

## 2. Create A User And Add It To The Organization

Create the password in a private terminal or restricted secret file. Do not commit the value:

```bash
export DEMO_USER=<demo-user>
export DEMO_USER_PASSWORD='[REDACTED]'
```

Generate the request body without hard-coding the password in docs:

```bash
python3 - <<'PY' >/tmp/gitea-demo-user.json
import json
import os

user = os.environ['DEMO_USER']
payload = {
    'username': user,
    'email': f'{user}@example.invalid',
    'full_name': 'Demo User',
    'password': os.environ['DEMO_USER_PASSWORD'],
    'must_change_password': False,
    'send_notify': False,
    'visibility': 'public',
}
print(json.dumps(payload))
PY

$CHATTEA api /admin/users \
  --method POST \
  --url "$GITEA_API" \
  --data "$(cat /tmp/gitea-demo-user.json)"

rm -f /tmp/gitea-demo-user.json
```

Add the user to an organization team. Resolve `OWNERS_TEAM_ID` from the actual team list output:

```bash
$CHATTEA api /orgs/$DEMO_ORG/teams --url "$GITEA_API"

export OWNERS_TEAM_ID=<team-id>

$CHATTEA api /teams/$OWNERS_TEAM_ID/members/$DEMO_USER \
  --method PUT \
  --url "$GITEA_API"
```

## 3. Create A Repository

ChatTea wraps repository creation:

```bash
export DEMO_REPO=<demo-repo>
export DEMO_FULL_REPO=$DEMO_ORG/$DEMO_REPO

$CHATTEA repo create \
  --owner "$DEMO_ORG" \
  --name "$DEMO_REPO" \
  --description 'Demo repository.' \
  --public \
  --default-branch main \
  --url "$GITEA_API" \
  --json-output \
  -I
```

Common repository inspection:

```bash
$CHATTEA repo view "$DEMO_FULL_REPO" --url "$GITEA_API" --json-output -I
$CHATTEA repo list --owner "$DEMO_ORG" --limit 10 --url "$GITEA_API" --json-output
```

## 4. Initialize Local Git And Configure Repo-Local Token

```bash
mkdir -p /tmp/chattea-quickstart
cd /tmp/chattea-quickstart

git init -b main
git config user.name 'ChatTea Quickstart Bot'
git config user.email 'chattea-quickstart@example.invalid'

cat > README.md <<EOF
# ChatTea Quickstart Demo

Created for \`$DEMO_FULL_REPO\`.
EOF

git add README.md
git commit -m 'docs: add quickstart readme'
```

Add the public remote using the no-`.git` form:

```bash
git remote add origin "$GITEA_PUBLIC/$DEMO_FULL_REPO"
```

Current `chattea set-token` writes repo-local git auth to `http.<url>.extraHeader` using a repository path normalized without `.git`. Keep the remote URL in the same no-`.git` shape until the CLI handles both forms.

Configure repo-local token without committing the token value:

```bash
CHATARCH_HOME="$PWD/.chatarch" \
  $CHATTEA set-token \
  --base-url "$GITEA_PUBLIC" \
  --token "$GITEA_TOKEN" \
  -I
```

Verify only the config key, not the header value:

```bash
git config --local --name-only --get-regexp '^http\..*\.extraHeader$'
```

Push main:

```bash
git push -u origin main
```

## 5. Push A Feature Branch

```bash
git switch -c <feature-branch>

cat >> README.md <<'EOF'
- This line is added from a feature branch and merged through a PR.
EOF

git add README.md
git commit -m 'docs: add quickstart branch note'
git push -u origin <feature-branch>
```

## 6. Issue Workflow

Create issue:

```bash
$CHATTEA issue create \
  --repo "$DEMO_FULL_REPO" \
  --title 'Quickstart tracking issue' \
  --body 'Track the end-to-end ChatTea/Gitea quickstart run.' \
  --url "$GITEA_API"
```

View, comment, list comments, and edit a comment:

```bash
export ISSUE=<issue-number>

$CHATTEA issue view "$ISSUE" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"

$CHATTEA issue comment create "$ISSUE" \
  --repo "$DEMO_FULL_REPO" \
  --body 'Issue comment from the quickstart demo.' \
  --url "$GITEA_API"

$CHATTEA issue comment list "$ISSUE" \
  --repo "$DEMO_FULL_REPO" \
  --json-output \
  --url "$GITEA_API"

export ISSUE_COMMENT=<comment-id>

$CHATTEA issue comment edit "$ISSUE_COMMENT" \
  --repo "$DEMO_FULL_REPO" \
  --issue "$ISSUE" \
  --body 'Edited issue comment from the quickstart demo.' \
  --url "$GITEA_API"
```

Close and reopen:

```bash
$CHATTEA issue close "$ISSUE" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA issue reopen "$ISSUE" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA issue close "$ISSUE" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
```

List by state:

```bash
$CHATTEA issue list --repo "$DEMO_FULL_REPO" --state open --url "$GITEA_API"
$CHATTEA issue list --repo "$DEMO_FULL_REPO" --state closed --url "$GITEA_API"
$CHATTEA issue list --repo "$DEMO_FULL_REPO" --state all --json-output --url "$GITEA_API"
```

## 7. Pull Request Workflow

Create PR:

```bash
$CHATTEA pr create \
  --repo "$DEMO_FULL_REPO" \
  --title 'Add quickstart branch note' \
  --head <feature-branch> \
  --base main \
  --body 'Demonstrate PR creation, comments, review, close/reopen, and merge.' \
  --url "$GITEA_API"
```

View PR details, changed files, and commits:

```bash
export PR=<pr-number>

$CHATTEA pr view "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA pr files "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA pr commits "$PR" --repo "$DEMO_FULL_REPO" --limit 10 --url "$GITEA_API"
```

Comment and review:

```bash
$CHATTEA pr comment create "$PR" \
  --repo "$DEMO_FULL_REPO" \
  --body 'PR comment from the quickstart demo.' \
  --url "$GITEA_API"

$CHATTEA pr comment list "$PR" \
  --repo "$DEMO_FULL_REPO" \
  --json-output \
  --url "$GITEA_API"

$CHATTEA pr review create "$PR" \
  --repo "$DEMO_FULL_REPO" \
  --body 'Review comment from the quickstart demo.' \
  --event COMMENT \
  --url "$GITEA_API"

$CHATTEA pr review list "$PR" \
  --repo "$DEMO_FULL_REPO" \
  --json-output \
  --url "$GITEA_API"
```

Close, reopen, and merge:

```bash
$CHATTEA pr close "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA pr reopen "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"

$CHATTEA pr merge "$PR" \
  --repo "$DEMO_FULL_REPO" \
  --method merge \
  --delete-branch \
  --title 'Merge quickstart branch note' \
  --message 'Merged by ChatTea quickstart demo.' \
  --url "$GITEA_API"
```

Sync main after merge:

```bash
git switch main
git pull --ff-only origin main
```

Useful list and diff commands:

```bash
$CHATTEA pr list --repo "$DEMO_FULL_REPO" --state open --url "$GITEA_API"
$CHATTEA pr list --repo "$DEMO_FULL_REPO" --state closed --url "$GITEA_API"
$CHATTEA pr list --repo "$DEMO_FULL_REPO" --state all --json-output --url "$GITEA_API"
$CHATTEA pr diff "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
$CHATTEA pr patch "$PR" --repo "$DEMO_FULL_REPO" --url "$GITEA_API"
```

## Basic Verification Checklist

A basic ChatTea/Gitea validation should cover:

- `chattea api /version` for API reachability;
- `chattea repo create/list/view` for repository API coverage;
- `chattea set-token` plus `git push` for git transport auth;
- `chattea issue create/view/comment/list/edit/close/reopen` for issue workflows;
- `chattea pr create/view/files/commits/comment/review/close/reopen/merge` for PR workflows;
- browser access to mock or sanitized public repo/issue/PR pages when UI rendering matters.

Do not commit real `GITEA_TOKEN`, `CHATTEA_TOKEN`, user passwords, certificate private keys, git extraHeader values, or live practice URLs.

## Infra Follow-ups Found By This Flow

These are not the main purpose of this docs pass, but the practiced flow exposed useful follow-ups:

- add first-class `org`, `user`, and `team` commands so the quick start no longer relies on raw `chattea api` calls;
- add an explicit `repo create --private` option to make public/private intent clearer;
- make `set-token` configure git auth for both remote URL shapes: `https://host/owner/repo` and `https://host/owner/repo.git`.
