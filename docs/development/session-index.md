# Session Index

**Date:** July 12, 2026  
**Project:** Johnny-Johnny Native iPhone Voice Controller  
**iOS App Version:** 1.0.0 baseline  
**Git Branch:** `dev`  
**Completed Story:** Native iPhone Voice Controller  
**Next Story:** Guided pgvector + LangChain + LangGraph RAG and Safe Tool Execution  
**Follow-on iPhone Story:** Automatically Send Voice Messages from Action-Button Invocation

## Session Summary

The first native Johnny-Johnny iPhone application was opened in Xcode, connected to a dedicated GitHub repository, configured for Apple signing, installed on Grant's iPhone 17 Pro Max, connected to a dedicated Auth0 Native application, and validated against the live Johnny-Johnny backend.

The end-to-end native path is working:

```text
Action Button / App Shortcut
→ Johnny-Johnny launches
→ native speech recognition
→ authenticated assistant API
→ model response
→ displayed and spoken response
```

The app was validated on a physical iPhone 17 Pro Max. Auth0 Universal Login, user-delegated API access, model loading, voice capture, assistant responses, local app settings, and the **Talk to Johnny-Johnny** App Shortcut all worked.

A first implementation of **Send on release** was also tested successfully for in-app push-to-talk. It does not yet complete the Action-button hands-free path because App Intents do not expose the physical Action-button release event to the application. That behavior has been split into a dedicated follow-on story based on silence completion.

## Stories Completed

### Native iPhone Voice Controller

Completed and physically validated:

- SwiftUI application opened and built in Xcode;
- dedicated `johnny-johnny-ios` Git repository established;
- Apple Developer Program agreement accepted;
- automatic signing and provisioning configured;
- physical iPhone registered and paired;
- app installed on iPhone 17 Pro Max;
- Auth0 Native application created;
- Authorization Code Flow with PKCE validated;
- user-delegated `invoke:assistant` access configured;
- Auth0 SSO behavior validated;
- authenticated model catalog loaded;
- voice transcription validated;
- assistant response display validated;
- assistant spoken response path validated;
- App Shortcut registered;
- Action button assigned to **Talk to Johnny-Johnny**;
- Action-button launch into listening mode validated.

## Current Story State

The native iPhone controller is operational and suitable as the client for the next RAG/tool-execution story.

The checked-in repository baseline is:

```text
3b3ad86 initial build of jj
```

Development is on:

```text
dev
```

The optional in-app **Send on release** change was reapplied after troubleshooting and worked when tested from inside the app.

## Next Recommended Story

Proceed with:

```text
Johnny-Johnny RAG and Tool-Execution Learning Story
```

The next story is a guided learning implementation using:

- PostgreSQL;
- pgvector;
- LangChain;
- LangGraph;
- OpenAI embeddings and language models;
- the existing authenticated assistant endpoint;
- the existing canonical backlog mutation capability;
- explicit human confirmation before mutation.

The first supported AI tool will update one existing backlog item's status and optionally append one comment through the existing canonical mutation and GitHub synchronization path.

## Follow-on iPhone Story

A durable story was created for hands-free completion:

```text
Automatically Send Voice Messages from Action-Button Invocation
```

The Action button launches an App Intent but does not provide a physical button-release event to the app. Therefore the correct hands-free behavior is:

```text
Action button launches Johnny-Johnny
→ listening begins
→ silence is detected
→ recognition finalizes
→ non-empty transcript sends automatically
```

## Engineering Artifacts Created

```text
docs/development/johnny-johnny-native-iphone-deployment-acceptance-2026-07-12.md
docs/development/johnny-johnny-action-button-auto-send-story.md
docs/development/BACKLOG-UPDATE-2026-07-12-native-iphone.md
docs/development/cookbooks/command-cheat-sheet-2026-07-12-044500.md
docs/development/session-index.md
```

## Engineering Artifacts Reviewed — No Update Required

### ADRs

Reviewed. No new ADR is required. The session implemented previously agreed architecture rather than introducing a new system-wide architecture decision.

### Architecture Documentation

Reviewed. The deployment acceptance document captures the validated native-client architecture and boundaries. No broader architecture document requires amendment.

### Specifications

Reviewed. The native iPhone story remains the governing specification. A separate follow-on specification was created for Action-button automatic send after silence.

### Database Documentation

Reviewed. No database schema or persistence behavior changed during this session.

### Engineering Principles

Reviewed. No new engineering principle was introduced. The implementation continues to preserve provider boundaries, server-owned orchestration, and explicit behavior.

### Working Agreement

Reviewed. No workflow amendment is required.

### AI Collaboration Documentation

Reviewed. The next RAG story already establishes the guided, one-concept-at-a-time teaching workflow.

### Behavior Tests

Reviewed. No repository behavior tests were added during this physical-device deployment session. The follow-on Action-button auto-send story explicitly requires tests for silence completion, empty transcripts, late final recognition, and API failure.

## Files Changed During the Session

Primary repository files configured or changed:

```text
JohnnyJohnny/Resources/Auth0.plist
JohnnyJohnny/Services/AppSettings.swift
JohnnyJohnny/ViewModels/AssistantViewModel.swift
JohnnyJohnny/Views/AssistantView.swift
JohnnyJohnny/Views/SettingsView.swift
```

Xcode also created or updated local signing, provisioning, package-resolution, indexing, and derived build state outside the logical application behavior.

## Architectural Decisions Confirmed

- The iPhone app is a separate deployable Git repository beside the agent and web UI repositories.
- Xcode opens and edits the repository files in place; it does not copy the project.
- The native app uses its own Auth0 **Native** application.
- The native app uses Authorization Code Flow with PKCE.
- No client secret is stored in the app.
- API access is user-delegated, not machine-to-machine.
- Existing Auth0 SSO may eliminate a repeated username/password prompt.
- The Action button invokes an App Shortcut/App Intent.
- Physical Action-button release is not available to the app as a continuous input event.
- Hands-free automatic send should therefore use silence completion and final speech-recognition output.
- The backend remains responsible for assistant orchestration, model policy, RAG, tools, authorization, and mutation execution.

## Bugs Discovered and Resolved

### SwiftUI Section initializer compilation error

`SettingsView.swift` initially used a `Section` form that Xcode resolved against the wrong initializer. The section declarations were replaced with explicit content/header/footer closures.

### Auth0 client not authorized

The dedicated Auth0 Native application initially lacked user-delegated API access. Grant enabled user-delegated access with the `invoke:assistant` permission.

### Device pairing and symbol preparation

The iPhone was initially unavailable while pairing and registration were incomplete. Reconnecting after registration allowed Xcode to copy symbols and complete device preparation.

### White-screen launch and stuck process

After reinstall/build cycles, the app sometimes remained on a white screen. Device logs showed that an application process already existed instead of a normal crash. Rebooting the iPhone cleared the stuck process and restored normal operation.

### Slow debug interaction

Settings toggles briefly responded slowly while the app was attached to Xcode and completing first-run debugger work. Performance normalized when running independently from Xcode.

### Send-on-release scope mismatch

The first implementation worked for the in-app push-to-talk gesture but not for Action-button invocation. This was not a simple defect in the toggle; it exposed a separate hands-free workflow requiring silence completion.

## Lessons Learned

- Put the iOS app in its own repository before ongoing development.
- Xcode source control and terminal Git operate on the same files and repository.
- Physical-device deployment includes Apple agreement, device registration, pairing, Developer Mode, provisioning, and symbol preparation.
- A public Auth0 Client ID is configuration, not a secret.
- Auth0 Native applications need user-delegated API authorization for signed-in user flows.
- Auth0 SSO can make a native login appear passwordless when a browser session already exists.
- Xcode and device-console warnings contain large amounts of unrelated operating-system noise.
- Filter logs by application process or bundle identifier before diagnosing.
- A white screen can be a stuck iOS process rather than an application crash.
- The Action button invokes a shortcut; it does not behave like an app-owned press-and-release control.
- Device-bound interaction behavior must be tested on the physical device, even when source parsing and compilation pass.

## Outstanding Work

### Native iPhone follow-on

- rename **Send on release** to a broader setting such as **Automatically send voice messages**;
- use silence completion for Action-button/App Shortcut invocation;
- wait for the final speech-recognition result;
- automatically send only non-empty transcripts;
- preserve review-before-send when automatic send is disabled;
- add behavior tests;
- commit and tag the proven iPhone state.

### Native app validation

- validate token refresh over time;
- validate logout and forced reauthentication;
- validate Bluetooth input/output routing;
- validate VoiceOver and larger Dynamic Type sizes;
- validate recovery from offline and API failure states;
- validate repeated Action-button invocations;
- decide whether to distribute later through TestFlight.

### RAG and safe tool execution

- inspect current assistant and backlog mutation capabilities;
- verify pgvector;
- choose embedding model and dimension;
- define retrieval documents;
- persist and query embeddings;
- add LangChain retrieval;
- add LangGraph state and confirmation interruption;
- execute confirmed mutations through the existing application use case.

## Next Recommended Starting Point

Begin the RAG story exactly as written: inspect the current authenticated assistant use case and the existing targeted backlog status/comment mutation capability before selecting libraries or changing schema.

## Files Likely Needed Next Session

```text
johnny-johnny-agent repository on branch dev
johnny-johnny-rag-tool-execution-story.md
docs/development/WORKING_AGREEMENT.md
docs/development/ENGINEERING_PRINCIPLES.md
docs/development/session-index.md
johnny-johnny-ios repository for later end-to-end validation
johnny-johnny-ui repository for later confirmation UI validation
```

## Immediate First Task

In the agent repository, locate and inspect:

1. the authenticated assistant request use case;
2. the canonical backlog item read capability;
3. the existing status/comment mutation use case;
4. the provider synchronization boundary;
5. the current PostgreSQL connection and migration structure.

Do not implement LangChain or LangGraph until these reuse boundaries are understood.
