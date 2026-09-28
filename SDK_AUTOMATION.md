# Node SDK update notifications

SDK updates can be started manually: **sullyai-node → Actions → Update SDK from OpenAPI → Run workflow**, select **main**, and leave `spec_sha` empty for current canonical main or supply a full main commit SHA. The workflow resolves and records the exact SHA, opens/updates one draft PR, and explicitly starts its CI. There is no cron or scheduled polling.

`.github/workflows/notify-node-sdk.yml` optionally notifies Node when `openapi.yaml` changes on main; manual replay on main is also available. It sends `repository_dispatch` type `openapi-updated` with the exact triggering SHA in `client_payload.spec_sha`. Node validates ancestry and orders updates against both its merged snapshot and pending PR, preventing stale/repeated events from rolling back the SDK.

## Configure a GitHub App later

1. In **Odiggo → Settings → Developer settings → GitHub Apps → New GitHub App**, choose an available name such as `Sully SDK Updates`. Set the Node repo URL as Homepage URL. Disable **Webhooks → Active**; no webhook server, subscriptions, callback URL or OAuth client secret is needed. Restrict installation to this account.
2. Grant repository **Contents: Read and write** and **Pull requests: Read and write**, plus implicit Metadata read. No Actions, Workflows, organization or account permission is needed.
3. Create the App, record its **App ID**, and **Generate a private key**. Under **Install App**, select Odiggo and **Only select repositories → sullyai-node**.
4. In **both repositories**, under **Settings → Secrets and variables → Actions**, add the PEM contents as repository secret **`SDK_APP_PRIVATE_KEY`**, then the numeric App ID as repository variable **`SDK_APP_ID`**. An organization secret/variable restricted to these two repos is also suitable. These workflows do not use environment secrets.
5. After both PRs land, run **sullyai-openapi → Actions → Notify Node SDK of OpenAPI changes → Run workflow → main**. Check the downstream Node run, generated PR when the spec differs, and SDK CI. Subsequent merges changing `openapi.yaml` will dispatch updates automatically.

The notifier mints a short-lived installation token restricted to Node and Contents write. Node requests Contents/PR write for bot changes and uses its own GITHUB_TOKEN for explicit CI dispatch. No PAT or registry token is needed. App-management/installation access in Odiggo is required to perform the setup.

The workflow never checks out or executes PR code. No App token is passed to spec-validation PR jobs, and no permission to bypass review or approve/merge PRs is requested. A configured but broken App causes an explicit failure.

## Before App setup

Without `SDK_APP_ID`, no notification is sent; the workflow summary directs the user to run the Node updater manually. No SDK App ID/key was found in accessible settings during implementation (2026-09-28), and live App dispatch has not been tested.

Manual updates use Node's repository token. Node must have Actions enabled and “Allow GitHub Actions to create and approve pull requests” enabled (verified enabled during implementation). The updater requests Contents/PR write and Actions write to explicitly dispatch read-only CI; ordinary GITHUB_TOKEN-created PR/push events are not relied on to start checks. Canonical OpenAPI is currently public. If it becomes private, configure narrowly scoped read access as well.

PR #19 is merged at `f7ad63f875ebbc972add1bb8eb578bc9a92a4460`; Node's initial snapshot tracks that verified main commit. Python, existing spec validation and required reviews are unchanged. No automatic merge or registry publication occurs.

References: [register a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app), [App token action](https://github.com/actions/create-github-app-token), [workflow token event behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
