# Repository settings

`repo-settings.yml` declares the shared settings for two public service
repositories. Each element of its `repos` list names a repository and says
which settings the fleet manages for it.

## Fleet bots

The `agents-md-sync` GitHub App is the fleet's standing bot. Its numeric App id
is `1234567` and it is installed on every managed repository.

## Ruleset bypass element reference

An element of `ruleset.bypass_actors` has these keys:

- `actor_type`: `Integration`, `Team`, `RepositoryRole`, `OrganizationAdmin` or
  `DeployKey` (for a GitHub App, `Integration`)
- `actor_id`: the numeric id (for `Integration`, the App id)
- `bypass_mode`: `always` or `pull_request`

A `bypass_actors` array in a repository's `overrides:` replaces the one in
`defaults:`; arrays are not merged.
