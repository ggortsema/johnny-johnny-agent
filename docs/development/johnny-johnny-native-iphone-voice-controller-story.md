# Johnny-Johnny Native iPhone Voice Controller Story

**Status:** Planned  
**Priority:** Next  
**Platform:** Native iPhone / SwiftUI  
**Primary purpose:** Voice-first controller for the Johnny-Johnny assistant

## Story

Build a native iPhone application that authenticates with Johnny-Johnny through Auth0 using Authorization Code Flow with PKCE and provides a polished, assistant-only, voice-first conversation experience.

The application should feel like a dedicated remote control for Johnny-Johnny rather than a mobile version of the web administration interface.

## Goals

- Make Johnny-Johnny easy to invoke and use from an iPhone.
- Make voice input the primary interaction model.
- Reuse the existing authenticated assistant API and server-owned model catalog.
- Preserve the existing domain and provider boundaries.
- Provide a clean foundation for future confirmation cards and assistant tool execution.

## Functional Requirements

### Authentication

- Use Auth0 Universal Login.
- Use Authorization Code Flow with PKCE.
- Use a native iOS Auth0 application configuration.
- Never ship an Auth0 client secret in the app.
- Store access and refresh tokens securely in the iOS Keychain.
- Support secure token refresh.
- Show the signed-in user.
- Support logout.
- Clearly handle expired or invalid authentication.

### Assistant Experience

- Provide one primary assistant conversation screen.
- Keep the interface centered on the assistant.
- Do not include Docs, Git, raw JSON, reconciliation, or admin screens.
- Display Johnny-Johnny responses as text.
- Preserve a local conversation transcript on the device.
- Support starting a new conversation.
- Support clearing the local conversation.
- Support copying a message.
- Support retrying a failed message.
- Support stopping an in-progress spoken response.

### Voice Input

- Provide a large press-and-hold microphone button as the primary control.
- Give haptic feedback when recording begins and ends.
- Show clear visual feedback while listening.
- Show live speech-to-text transcription.
- Allow the transcript to be reviewed and edited before sending.
- Allow the transcript to be cancelled.
- Provide normal text input as a fallback.
- Support silence-based completion where appropriate, without requiring always-on listening.

### Spoken Responses

- Display every assistant response as text.
- Support manual read-aloud.
- Support automatic read-aloud through a user setting.
- Provide a stop-speaking control.
- Use the active iOS audio route, including Bluetooth headsets when available.

### Model Selection

- Load the model catalog from the Johnny-Johnny backend.
- Show only models returned by the authenticated server-owned allowlist.
- Remember the last selected model locally.
- Use the backend default model when no local preference exists.

### Action Button, Siri, and Shortcuts

- Define an App Intent/App Shortcut named **Talk to Johnny-Johnny**.
- Make the shortcut available to Siri and the Shortcuts app.
- Support assigning the shortcut to the iPhone Action button.
- Launch the app directly into listening mode when invoked through the shortcut.
- Provide immediate haptic and visual feedback when listening begins.

### Interaction States

The UI must make these states explicit:

- Ready
- Listening
- Transcribing
- Review
- Sending
- Johnny-Johnny is thinking
- Speaking
- Offline
- Authentication expired
- Request failed

### Keep Awake

- Provide an explicit Keep Awake setting.
- Prevent screen dimming only while the setting is enabled and the app is active.
- Restore normal device behavior when disabled or when the app leaves the foreground.

## Non-Functional Requirements

- Use SwiftUI.
- Keep the first version intentionally focused.
- Use native iOS APIs for speech recognition, speech synthesis, haptics, audio routing, and secure storage where practical.
- Preserve accessibility, Dynamic Type, VoiceOver labels, and usable contrast.
- Use explicit, testable API client boundaries.
- Normalize Johnny-Johnny API errors into user-friendly application states.
- Avoid moving assistant orchestration into the phone.
- Keep conversation memory local until a backend conversation capability is intentionally designed.

## Explicitly Out of Scope

- Documentation browsing
- Git/backlog administration screens
- Reconciliation controls
- Raw JSON views
- Background always-on listening
- Custom wake-word detection
- CarPlay
- Push notifications
- Offline language models
- Server-side conversation memory
- Direct GitHub access from the app
- Tool execution without explicit backend authorization and confirmation

## Expected API Usage

The app will use the existing public HTTPS origin:

```text
https://johnny-johnny.mycroftai.org
```

Expected authenticated API surfaces include:

```text
GET  /api/v1/auth/whoami
GET  /api/v1/assistant/models
POST /api/v1/assistant/responses
```

The API remains responsible for:

- validating Auth0 access tokens;
- enforcing permissions;
- selecting allowed models;
- invoking the language-model provider;
- normalizing assistant responses;
- later coordinating tools, RAG, and confirmation workflows.

## Device Delivery Requirements

After the code is created, complete the installation path step by step:

1. Open the project in Xcode.
2. Select the correct Apple developer team.
3. Configure a unique bundle identifier.
4. Configure Auth0 callback and logout URL schemes.
5. Enable required capabilities.
6. Configure signing and provisioning.
7. Connect and trust the target iPhone.
8. Build and run on the device.
9. Validate login and token refresh.
10. Validate microphone permission and transcription.
11. Validate spoken responses.
12. Validate model selection.
13. Register the App Shortcut.
14. Assign **Talk to Johnny-Johnny** to the Action button.
15. Validate Action-button launch into listening mode.

## Acceptance Criteria

- The user can install and launch the app on their iPhone.
- The user can sign in through Auth0 using PKCE.
- Tokens are stored securely.
- The app can load the authenticated model catalog.
- The user can press and hold to dictate a message.
- Live transcription is shown.
- The transcript can be edited before sending.
- The assistant response is shown as text.
- The assistant response can be read aloud.
- Automatic read-aloud can be enabled or disabled.
- The app supports text input.
- The local transcript can be cleared.
- Keep Awake works only when enabled.
- The App Shortcut is available.
- The Action button can launch Johnny-Johnny directly into listening mode.
- Authentication, offline, API, and permission failures are clearly represented.
- No Auth0 client secret or provider credential is present in the app.
