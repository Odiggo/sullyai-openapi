# Node SDK update notifications

SDK updates can be started manually: **sullyai-node → Actions → Update SDK from OpenAPI → Run workflow**, select **main**, and leave `spec_sha` empty for current canonical main or supply a full main commit SHA. The workflow resolves and records the exact SHA, opens/updates one draft PR, and explicitly starts its CI. There is no cron or scheduled polling.

`.github/workflows/notify-node-sdk.yml` optionally notifies Node when `openapi.yaml` changes on main; manual replay on main is also available. It sends `repository_dispatch` type `openapi-updated` with the exact triggering SHA in `client_payload.spec_sha`. Node validates ancestry and orders updates against both its merged snapshot and pending PR, preventing stale/repeated events from rolling back the SDK.

## Configure a GitHub App later

1. In **Odiggo → Settings → Developer settings → GitHub Apps → New GitHub App**, choose an available name such as `Sully SDK Updates`. Set the Node repo URL as Homepage URL. Disable **Webhooks → Active**; no webhook server, subscriptions, callback URL or OAuth client secret is needed. Restrict installation to this account.
2. Grant repository **Contents: Read and write** and **Pull requests: Read and write**, plus implicit Metadata read. No Actions, Workflows, organization or account permission is needed.
3. Create the App, record its **Client ID**, and **Generate a private key**. Under **Install App**, select Odiggo and **Only select repositories → sullyai-node**.
4. In **both repositories**, under **Settings → Secrets and variables → Actions**, add the PEM contents as repository secret **`SDK_APP_PRIVATE_KEY`**, then the Client ID as repository variable **`SDK_APP_CLIENT_ID`**. An organization secret/variable restricted to these two repos is also suitable. These workflows do not use environment secrets.
5. After both PRs land, run **sullyai-openapi → Actions → Notify Node SDK of OpenAPI changes → Run workflow → main**. Check the downstream Node run, generated PR when the spec differs, and SDK CI. Subsequent merges changing `openapi.yaml` will dispatch updates automatically.

The notifier mints a short-lived installation token restricted to Node and Contents write. Node requests Contents/PR write for bot changes and uses its own GITHUB_TOKEN for explicit CI dispatch. No PAT or registry token is needed. App-management/installation access in Odiggo is required to perform the setup.

The workflow never checks out or executes PR code. No App token is passed to spec-validation PR jobs, and no permission to bypass review or approve/merge PRs is requested. A configured but broken App causes an explicit failure.

## Before App setup

Without `SDK_APP_CLIENT_ID`, no notification is sent; the workflow summary directs the user to run the Node updater manually. No SDK App client ID/key was found in accessible settings during implementation (2026-09-28), and live App dispatch has not been tested.

Manual updates use Node's repository token. Node must have Actions enabled and “Allow GitHub Actions to create and approve pull requests” enabled (verified enabled during implementation). The updater requests Contents/PR write and Actions write to explicitly dispatch read-only CI; ordinary GITHUB_TOKEN-created PR/push events are not relied on to start checks. Canonical OpenAPI is currently public. If it becomes private, configure narrowly scoped read access as well.

PR #19 is merged at `f7ad63f875ebbc972add1bb8eb578bc9a92a4460`; Node's initial snapshot tracks that verified main commit. Existing spec validation and required reviews are unchanged. No automatic merge or registry publication occurs.

References: [register a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app), [App token action](https://github.com/actions/create-github-app-token), [workflow token event behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

### Private-key parsing errors

`Invalid keyData` or ASN.1 `wrong tag` means the signing key could not be parsed; changing the client ID does not repair the key. Set `SDK_APP_PRIVATE_KEY` to the complete downloaded GitHub App PEM file, including its original BEGIN/END lines and all line breaks. Do not use the OAuth client secret or change the PEM header. Validate the downloaded file without displaying its contents using `openssl pkey -in /path/to/app.pem -check -noout`, then upload it directly with `gh secret set SDK_APP_PRIVATE_KEY --repo Odiggo/sullyai-openapi < /path/to/app.pem` and the same command for `Odiggo/sullyai-node`.

## Python SDK notifications

`.github/workflows/notify-python-sdk.yml` uses the same pinned-generator update protocol for [sullyai-python](https://github.com/Odiggo/sullyai-python). It runs independently of the Node notifier, so a Python configuration failure cannot block Node notifications. A push changing `openapi.yaml` on main sends the exact source SHA; the workflow also supports manual replay on main.

Before enabling automatic Python updates, open the existing **Sully SDK Updates** GitHub App installation in Odiggo and add **sullyai-python** to its selected repositories. Keep the existing Contents write permission. Reuse the `SDK_APP_CLIENT_ID` variable and `SDK_APP_PRIVATE_KEY` secret already configured in this OpenAPI repository. No new key or secret is needed here.

The Python updater can use its repository `GITHUB_TOKEN` to commit and create its draft PR, then explicitly dispatch read-only SDK CI. Consequently, Python needs no copy of the App key for this setup. Its Actions setting **Allow GitHub Actions to create and approve pull requests** must be enabled. Optionally configure the same App ID/key in Python to match Node's App-authenticated commits.

After the Python repository has its workflows on main and this notifier is merged, run **Notify Python SDK of OpenAPI changes** on main. Verify the downstream **Update SDK from OpenAPI** run, and (when contract contents differ) the draft PR and SDK CI. Same-content or repeated dispatches produce no duplicate PR. There is no automatic merge or PyPI publication.
