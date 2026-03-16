# Neon Protocol - Project Setup

This folder contains the core scripts for the **Neon Protocol** Android FPS.

## Installation
1.  **Copy Files:** Drag the `Assets` folder into your Unity Project's `Assets` directory.
2.  **Dependencies:** Ensure you have the **New Input System** package installed via Package Manager.
3.  **Setup:**
    - **Input:** Attach `NeonInputHandler` to a persistent GameObject. Assign the `PlayerInput` asset.
    - **Movement:** Attach `NeonMovement` to your Player object (requires `CharacterController`).
    - **Pooling:** Attach `NeonPooler` to a Manager object. Populate the `Pools` list with Zombie/Bullet prefabs.
    - **Quests:** Attach `QuestManager` to a Manager object. Select the current `MapTheme`.

## Setting Up the Build

The CI workflow (`.github/workflows/main.yml`) builds an Android APK automatically on every push to `main` and can also be triggered manually. It requires three GitHub repository secrets to be configured with your Unity license credentials.

### One-Time License Setup

1. **Generate an activation file** – Go to the **Actions** tab, select **Unity License Activation**, click **Run workflow**, and download the `Unity-Activation-File` artifact (a `.alf` file).
2. **Get a license file** – Visit [https://license.unity3d.com](https://license.unity3d.com), sign in with your Unity account, upload the `.alf` file, and download the returned `.ulf` license file.
3. **Add secrets** – In the repository go to **Settings → Secrets and variables → Actions** and add:
   | Secret name | Value |
   |---|---|
   | `UNITY_LICENSE` | Full text content of the downloaded `.ulf` file |
   | `UNITY_EMAIL` | Your Unity account email address |
   | `UNITY_PASSWORD` | Your Unity account password |

### Triggering a Build

- **Automatic** – Every push to the `main` branch triggers a build.
- **Manual** – Go to **Actions → Neon Protocol Android Forge → Run workflow**.

The compiled `NeonProtocol.apk` is uploaded as the `NeonProtocol-Android-Build` artifact after a successful build.

## Modules
- **Core/Input:** Handles Touch vs Gamepad switching.
- **Core/Movement:** Implements IW-style G-Slide and Bunny Hopping.
- **Core/Systems:** Object Pooling and Quest Management.
- **Maps:** Specific logic for Spaceland (UFO), Rave (Vision), Shaolin (Chi), Radioactive (Chemistry), and Beast (Cryptids).
