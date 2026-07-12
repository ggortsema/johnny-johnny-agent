# Command Cheat Sheet — Johnny-Johnny Native iPhone Session

**Timestamp:** 2026-07-12 04:45:00 EDT  
**Purpose:** Commands used or instructed during native iPhone setup, Auth0 configuration, source-control recovery, and troubleshooting.

> Public identifiers are represented with placeholders where appropriate. No secret values are included.

## Bash / Shell

### Enter the iOS repository

```bash
cd /path/to/johnny-johnny-ios
```

Moves the shell into the native iOS repository before running project scripts or Git commands.

### Configure the Auth0 Native Client ID

```bash
./scripts/configure-auth0.sh 'YOUR_NATIVE_AUTH0_CLIENT_ID'
```

Writes the public Auth0 Native application Client ID into `JohnnyJohnny/Resources/Auth0.plist` and prints the required callback/logout URL.

## Git

### Create a source archive of the current committed repository

```bash
git archive --format=zip --output=johnny-johnny-ios-current.zip HEAD
```

Creates a ZIP from the committed `HEAD` without including `.git` metadata. This was proposed as the safest way to provide the exact current repository state for an update.

### Restore the four voice/settings files to the current committed version

```bash
git restore \
  JohnnyJohnny/Services/AppSettings.swift \
  JohnnyJohnny/ViewModels/AssistantViewModel.swift \
  JohnnyJohnny/Views/AssistantView.swift \
  JohnnyJohnny/Views/SettingsView.swift
```

Reverted the four experimental **Send on release** files to the last committed state while diagnosing the white-screen behavior.

### Verify the working tree

```bash
git status --short
```

Confirmed that the four restored files matched the committed baseline and that the working tree was clean.

### Inspect recent commit history

```bash
git log --oneline --decorate -8
```

Verified the current branch, remote-tracking branches, tag, and the committed native-app baseline.

Observed result:

```text
3b3ad86 (HEAD -> dev, tag: initial, origin/main, origin/dev, main) initial build of jj
facbb1e initial commit
```

## Xcode / Device Operations

These are UI operations rather than shell commands, but they were important to the installation and troubleshooting workflow.

### Open the existing project in place

```text
JohnnyJohnny.xcodeproj
```

Xcode opens and edits the files in the Git repository directly; it does not copy or reimport them.

### Open device management

```text
Window → Devices and Simulators
```

Used to register, pair, inspect, and prepare the physical iPhone.

### Clean derived build output

```text
Product → Clean Build Folder
```

Removes Xcode's derived build artifacts before rebuilding. Hold Option if Xcode only shows **Clean Build**.

### Run on the selected iPhone

```text
Run ▶︎
```

Builds, installs, launches, and attaches the debugger to the selected physical device.

### Activate the debug console

```text
View → Debug Area → Activate Console
```

Opens Xcode's runtime console.

Keyboard shortcut used/instructed:

```text
Shift-Command-C
```

### Open the report navigator

```text
Command-9
```

Shows build and run reports, including build success, install, launch, and debugger-attachment phases.

### Inspect or edit the run scheme

```text
Product → Scheme → Edit Scheme…
```

Used to verify that the **Run** action was configured to launch automatically.

### Attach to a manually launched process

```text
Debug → Attach to Process by PID or Name…
```

Used while investigating a manually opened app that showed a white screen.

### Filter device logs

```text
process:JohnnyJohnny
```

Filters the device Console for the Johnny-Johnny process.

Fallback bundle-identifier filter:

```text
org.mycroftai.johnnyjohnny
```

Filters device logs by the application's bundle identifier.

## Auth0 Dashboard Configuration

These are dashboard values rather than terminal commands.

### Application type

```text
Native
```

The iPhone app uses a dedicated Auth0 Native application.

### Callback and logout URL

```text
org.mycroftai.johnnyjohnny://dev-ude3gljkecu7ylzt.us.auth0.com/ios/org.mycroftai.johnnyjohnny/callback
```

Registered in both **Allowed Callback URLs** and **Allowed Logout URLs**.

### API access mode

```text
User-Delegated Access
```

Correct mode for a signed-in user calling the Johnny-Johnny API through PKCE.

### Permission

```text
invoke:assistant
```

Allows the authenticated native client to invoke the assistant API.

## Troubleshooting Lessons

- A clean Git status proves that files match the current commit, not that the current commit is necessarily the previously working version.
- Xcode/device logs contain extensive unrelated operating-system noise; filter by process or bundle identifier.
- A white screen may represent a stuck iOS process rather than a code crash.
- When iOS reports that an app process already exists after force-close/reinstall attempts, a device restart can clear the stale process.
- Debug builds may feel temporarily sluggish while Xcode installs, attaches, prepares symbols, or performs first-run work.
