# ChatTea CLI Capability Map

This page is a compact capability map for the current ChatTea CLI. Use it to review which Gitea flows are already first-class ChatTea commands and which still require `chattea api`.

For the importable Python function mapping, see [Interface Tree](interface-tree.md). For longer screenshots and route evidence, see [ChatTea CLI Guide](cli-guide.md).

## Top-Level Commands

```text
chattea
├── api                 # call raw Gitea API paths not yet wrapped by ChatTea
├── artifact            # inspect, download, and delete Gitea Actions artifacts
├── auth                # configure and inspect ChatTea base URL / token state
├── issue               # manage repository issues, issue comments, labels, assignees
├── job                 # inspect or rerun Gitea Actions jobs
├── label               # manage repository labels
├── milestone           # manage repository milestones
├── pr                  # manage pull requests, PR comments, reviews, diff/patch, merge
├── project             # manage Gitea repo project boards, columns, and issue/PR cards
├── release             # manage repository releases and release assets
├── repo                # create, view, list, clone, and migrate repositories
├── run                 # inspect or control Gitea Actions workflow runs
├── runner              # manage Gitea Actions runners and runner registration tokens
├── server              # install, initialize, start, and inspect the managed Gitea service
├── set-token           # configure ChatTea API token and repo-local git auth
└── token               # create, list, delete, and bootstrap Gitea access tokens
```

## Raw API

```text
chattea api PATH
  --method GET|POST|PUT|PATCH|DELETE
  --data JSON
  --param KEY=VALUE
```

Current practiced uses:

- `POST /orgs`: create an organization;
- `POST /admin/users`: create a user;
- `GET /orgs/{org}/teams`: inspect organization teams;
- `PUT /teams/{id}/members/{username}`: add a user to a team.

These are good candidates for first-class ChatTea wrappers once the docs flow stabilizes.

## Auth And Token

```text
chattea auth
├── login               # write ChatTea base URL / token and try repo-local git auth
├── status              # show current base URL and masked token state
└── token               # show masked token for confirmation

chattea set-token       # legacy/shortcut login entry, often used inside a git repo

chattea token
├── bootstrap           # create a token, then configure ChatTea/Git credentials
├── create              # create an access token with username/password BasicAuth
├── delete              # delete an access token by id or name
└── list                # list access tokens with username/password BasicAuth
```

Current practical note: `chattea set-token` writes repo-local git auth to `http.<url>.extraHeader`. The practiced flow found that remotes without `.git` work with the current normalization. Remotes with `.git` need an implementation follow-up so both URL shapes are configured.

## Repository

```text
chattea repo
├── clone               # clone from the configured Gitea base URL
├── create              # create a user or organization repository
├── list                # list repositories for the current user or an owner
├── migrate             # migrate from an existing Git URL into Gitea
└── view                # view an owner/name repository
```

Permission-related behavior verified by the docs flow:

- `repo create --public` creates a public repository;
- omitting `--public` creates a private repository;
- current ChatTea does not expose an explicit `--private` option;
- current normal repository create/edit flow does not expose a repo-level `internal` visibility input.

## Issue

```text
chattea issue
├── create              # create an issue
├── list                # list issues by open/closed/all state
├── view                # view issue details
├── edit                # edit title, body, state, labels, milestone, assignees
├── close               # close an issue
├── reopen              # reopen an issue
├── delete              # delete an issue, with confirmation
├── comment
│   ├── create          # add an issue comment
│   ├── list            # list issue comments
│   ├── edit            # edit an issue comment
│   └── delete          # delete an issue comment, with confirmation
├── label
│   ├── add             # add label IDs to an issue
│   └── remove          # remove a label ID from an issue
└── assign
    ├── add             # add issue assignees
    └── remove          # remove issue assignees
```

The practiced quick start covered create, view, comment create/list/edit, close, reopen, and state-filtered list.

## Pull Request

```text
chattea pr
├── create              # create a PR from a head branch into a base branch
├── list                # list PRs by open/closed/all state
├── view                # view PR details
├── edit                # edit PR title, body, state, or base
├── close               # close a PR
├── reopen              # reopen a PR
├── merge               # merge a PR with merge/rebase/squash/fast-forward methods
├── diff                # output PR diff
├── patch               # output PR patch
├── commits             # list PR commits
├── files               # list changed files
├── comment
│   ├── create          # add a PR issue-comment
│   └── list            # list PR issue-comments
└── review
    ├── create          # create a PR review event
    ├── list            # list PR reviews
    └── submit          # submit an existing pending review
```

The practiced quick start covered create, view, files, commits, comment, review, close, reopen, and merge.

## Labels And Milestones

```text
chattea label
├── create
├── list
├── view
├── edit
└── delete

chattea milestone
├── create
├── list
├── view
├── edit
├── close
└── delete
```

These commands support issue and PR workflows through label IDs and milestone IDs.

## Project Boards

```text
chattea project
├── create              # create a repo-scoped project board
├── list                # list repo projects
├── view                # view a repo project
├── edit                # edit a repo project
├── delete              # delete a repo project
├── column
│   ├── create          # create a project column
│   ├── list            # list project columns
│   ├── edit            # edit a project column
│   └── delete          # delete a project column
├── card                # issue/PR card helpers
│   ├── add
│   ├── list
│   ├── move
│   └── remove
└── issue               # compatibility alias for card helpers
```

Use `project card` in new docs and automation. `project issue` remains a compatibility alias.

## Releases

```text
chattea release
├── create
├── list
├── view
├── latest
├── by-tag
├── edit
├── delete
└── asset
    ├── list
    └── delete
```

Release asset upload remains outside the current first-class surface until the HTTP client grows multipart upload support.

## Actions: Runs, Jobs, Artifacts, Runner

```text
chattea run
├── list
├── view
├── jobs
├── logs
├── rerun
├── rerun-failed
└── delete

chattea job
├── view
├── logs
└── rerun

chattea artifact
├── list
├── view
├── download
└── delete

chattea runner
├── setup               # install, register, and manage the local runner
├── list
├── view
├── edit
├── delete
└── token               # get a runner registration token
    ├── --scope repo    # requires --repo OWNER/NAME
    ├── --scope org     # requires --org ORG
    ├── --scope user
    └── --scope admin
```

These commands cover the first Gitea Actions surface: runner lifecycle, PR-triggered runs, jobs, logs, and artifacts.

## Server

```text
chattea server
├── bootstrap           # install/init Gitea, create admin/token, write ChatTea config
├── install             # download the ChatArch Gitea binary
├── init                # create a minimal app.ini
├── start               # install and start the user systemd service
├── stop                # stop the user systemd service
├── restart             # restart the user systemd service
├── status              # inspect user systemd service status
├── logs                # read service logs
├── health              # check Gitea API reachability
├── config              # view/edit managed app.ini values
├── version             # inspect binary or server version
└── serve               # run Gitea in the foreground for debugging
```

The managed service is operated by `chattea-gitea.service`; runner operations use `chattea-runner.service`.

## Current Wrapper Gaps

The recent quick start and permissions practice still needed raw API for:

- organization create/view/list;
- admin user create/view/list;
- team list/add-member/remove-member;
- user-owned repository creation through an admin create-as-user path;
- explicit `repo create --private` intent;
- `set-token` support for remote URLs both with and without a trailing `.git`.

Treat these as flow-discovered Infra follow-ups. They should be implemented only when a docs or practice flow needs them, then this page should be updated with the new first-class command shape.
