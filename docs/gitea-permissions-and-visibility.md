# Gitea Permissions, Visibility, And Token Scope

This page explains the Gitea visibility model we practiced through ChatTea: what anonymous users can see, what requires login or token access, and how organizations, users, teams, and repositories relate to each other.

The concrete verification objects and live URLs stay in local project records. This committed doc uses placeholders and result shapes only.

## Two Meanings Of Scope

There are two separate concepts that are easy to mix up:

1. visibility scope: who can see an object;
2. access token scope: which APIs a token can call.

This page mainly covers visibility scope. Token scope is covered separately near the end.

## Repository Visibility: Public / Private

Current ChatTea `repo create` and the Gitea normal repository create API cover public/private repository visibility:

- `chattea repo create ... --public` creates a public repository;
- omitting `--public` currently creates a private repository;
- Gitea `CreateRepoOption` and `EditRepoOption` expose a `private` field;
- API responses may include `internal: false`, but the normal create/edit options used in this flow do not expose a GitHub Enterprise-style `internal` repository input.

Verification result shape:

| Repository shape | `private` | Anonymous API | Anonymous HTML | Anonymous `git ls-remote` | Token API | Token `git ls-remote` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| public org repo | false | 200 | 200 | 0 | 200 | 0 |
| private org repo | true | 404 | 404 | 128 | 200 | 0 |
| public user repo | false | 200 | 200 | 0 | 200 | 0 |
| private user repo | true | 404 | 404 | 128 | 200 | 0 |

Interpretation:

- anonymous users can see public repository pages and API metadata, and can clone public repositories;
- anonymous users get `404` for private repositories, which avoids exposing that the repository exists;
- a token with enough permission can access private repository API metadata and git transport;
- user repositories and organization repositories behave the same way for public/private access.

## User And Organization Visibility: Public / Limited / Private

Gitea users and organizations support three visibility values:

- `public`: visible to everyone, including anonymous users;
- `limited`: visible to logged-in users;
- `private`: visible only to self, members, admins, or other authorized subjects.

Relevant API option fields:

- `CreateUserOption.Visibility` supports `public`, `limited`, and `private`;
- `CreateOrgOption.Visibility` supports `public`, `limited`, and `private`.

Verification result shape for users:

| User visibility | Anonymous API | Anonymous HTML | Admin token API |
| --- | ---: | ---: | ---: |
| public | 200 | 200 | 200 |
| limited | 404 | 404 | 200 |
| private | 404 | 404 | 200 |

Verification result shape for organizations:

| Organization visibility | Anonymous API | Anonymous HTML | Admin token API |
| --- | ---: | ---: | ---: |
| public | 200 | 200 | 200 |
| limited | 404 | 404 | 200 |
| private | 404 | 404 | 200 |

The token check above used an admin token. A normal logged-in user's access also depends on whether the user is the object owner, an organization member, a team member, or an admin.

## Organizations, Members, And Teams

Gitea organization permissions are team-based:

- one organization can have multiple teams;
- users become organization members by joining teams;
- teams decide repository permissions for their members;
- teams can include all repositories or selected repositories;
- teams can allow or deny organization repository creation;
- teams also have their own visibility.

The quick start mainly uses the automatically created `Owners` team, which has owner permission and includes all organization repositories.

Common team API shapes used by the quick start:

```text
GET /api/v1/orgs/<demo-org>/teams
PUT /api/v1/teams/<team-id>/members/<demo-user>
```

Team visibility meaning:

- `public`: any logged-in user can list the team;
- `limited`: organization members and organization owners can list the team;
- `private`: team members and organization owners can list the team;
- team visibility is still constrained by organization visibility.

## GitHub Similarities And Differences

Similarities:

- both systems have user repositories and organization repositories;
- both systems have public/private repositories;
- public repositories can be browsed and cloned anonymously;
- private repositories are hidden from anonymous users;
- organizations use members and teams for permissions;
- tokens can authenticate API and git transport operations.

Differences and unverified areas:

- GitHub Enterprise often has `internal` repository visibility, but the Gitea normal create/edit API path used here does not expose it as an input;
- current ChatTea `repo create` exposes `--public`; omitting it means private, but there is not yet an explicit `--private` flag;
- Gitea user/org `limited` and `private` visibility are not the same concept as repository visibility;
- team visibility controls whether the team itself can be listed, not repository visibility directly.

## Access Token Scope

Bootstrap and admin quick starts often use a broad token scope:

```text
all
```

That is convenient for bootstrap and admin-level practice flows. Production automation should prefer narrower scopes once the exact API surface is known.

ChatTea supports token management:

```bash
chattea token list
chattea token create --help
chattea token bootstrap --help
```

When writing docs or logs, include token name and scope only. Never include token values.

## Screenshot Policy

Do not commit screenshots from real Gitea instances if they expose real hostnames, object names, user names, organization names, repository names, tokens, or machine paths. If screenshots are needed, use mock objects and mock hostnames, or keep real captures in local project records outside the repository.

## Infra Follow-ups Found By This Flow

The permissions practice exposed several future ChatTea improvements:

- first-class `org create/view/list` commands to avoid raw API calls for organization setup;
- first-class `user create/view/list` or admin-user commands for controlled local Gitea practice environments;
- first-class `team list/add-member/remove-member` commands for organization membership flows;
- explicit `repo create --private` to make the public/private choice clear;
- `set-token` compatibility for remotes with and without a trailing `.git` suffix;
- separate investigation before documenting any GitHub-style `internal` repository visibility.
