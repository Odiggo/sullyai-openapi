# Node SDK update notifications

`.github/workflows/notify-node-sdk.yml` runs on main when `openapi.yaml` changes and can be replayed manually on main. It sends `repository_dispatch` type `openapi-updated` to `Odiggo/sullyai-node` with the exact triggering main commit SHA in `client_payload.spec_sha`. Node validates canonical-main ancestry and orders updates against both its merged snapshot and its existing update PR, so stale or repeated dispatches cannot roll back the SDK.

This does not generate, release, publish or merge either SDK. Python is unchanged. The existing `build` validation workflow and review protections are unchanged.

## Preferred authentication

Create a dedicated GitHub App, installed on **Odiggo/sullyai-node only**, with repository Contents read/write and Pull requests read/write (the latter is for Node's SDK bot PRs). Put `SDK_APP_ID` in Actions repository variables and `SDK_APP_PRIVATE_KEY` in Actions secrets in both the OpenAPI and Node repositories, or restrict organization values to these two repositories. Configure ID and key together. The notifier mints a short-lived installation token restricted to Node and Contents write; dispatch requires that permission. Node requests Contents/PR write for its bot changes and uses its own GITHUB_TOKEN for explicit CI dispatch, so the App needs no Actions permission. No PAT, npm token or PyPI token is needed.

The workflow never checks out or executes PR code. No App token is passed to spec-validation PR jobs, and no permission to bypass review or approve/merge PRs is requested. A configured but broken App causes an explicit failure; it is not silently ignored.

## Without an App

No SDK App ID/key was found in the repository settings accessible during implementation (2026-09-28). With no `SDK_APP_ID`, the notifier reports that no notification was sent. The companion Node implementation includes a six-hour polling schedule. Since this canonical repository is currently public, polling needs no cross-repository secret. Node must have Actions enabled, repository-token Contents/PR write permission, and “Allow GitHub Actions to create and approve pull requests” enabled (verified enabled in Node during implementation). It requests Actions write to explicitly dispatch read-only CI on the generated branch: ordinary GITHUB_TOKEN-created PR/push events must not be relied on to start CI.

Both workflows become active after their PRs are reviewed and merged into main. After the Node workflow lands, run “Update SDK from OpenAPI” on Node main once or wait for polling, and verify its generated PR's checks and `.tgz` artifact. This implementation has not exercised a live App-authenticated dispatch; credentials do not exist yet. If canonical OpenAPI becomes private, configure read access for polling as well.

PR #19 is already merged at `f7ad63f875ebbc972add1bb8eb578bc9a92a4460`; the Node snapshot was moved to that verified main commit. The Node updater also tests a bootstrap gate for the pre-merge case and supports squash-merge transition. No review or protected branch is bypassed.

References: [workflow token event behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow), [repository dispatch API](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event).
