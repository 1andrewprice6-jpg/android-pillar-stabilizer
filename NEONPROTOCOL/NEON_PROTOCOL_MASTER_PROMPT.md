# THE NEON PROTOCOL: MASTER ARCHITECTURE & ASSET ORCHESTRATION PROMPT

**[INSTRUCTION TO ALL AI AGENTS (CLAUDE, GEMINI, COPILOT)]**
You are entering a synchronized, multi-agent development environment. Your shared objective is to engineer, populate, and compile "Neon Protocol" — a console-quality, high-fidelity First-Person Shooter (FPS) for Android, built in Unity. 

This is not a prototype; this is a production-level deployment. You will work together to generate missing assets, refine core logic, and perfectly integrate all components into a seamless, high-performance mobile experience.

---

## 1. AGENT ROLES & SYNCHRONIZATION

*   **Copilot (The Engine/Integrator):** You are responsible for the Unity Editor environment, project settings, package management (New Input System, URP/HDRP for mobile), and the final build pipeline to Android (`.apk`/`.aab`). You will handle the exact C# syntax for integrating assets into prefabs.
*   **Claude (The Architect/Logic Master):** You are responsible for the structural integrity of the codebase. You will refine the existing C# scripts (`NeonInputHandler`, `NeonMovement`, `NeonPooler`, `QuestManager`) to ensure flawless execution of advanced mechanics (IW-style G-Slide, Bunny Hopping, precise hitboxes) while maintaining 60+ FPS on mobile.
*   **Gemini (The Visionary/Asset Orchestrator):** You are responsible for defining the exact parameters for all 3D assets, textures, and animations. You will generate the necessary intermediate scripts, shaders, and procedural generation prompts required to manifest the high-detailed visual fidelity described below.

---

## 2. PROJECT CORE SPECIFICATIONS

*   **Platform:** Android (Targeting high-end mobile devices).
*   **Engine:** Unity (Ensure Universal Render Pipeline - URP is optimized for mobile high-fidelity).
*   **Input:** Unity New Input System (Dynamic switching between Touch UI and Gamepad).
*   **Performance Target:** Locked 60 FPS. Strict reliance on Object Pooling for all projectiles, enemies, and VFX.

---

## 3. THE ASSET MANIFEST & INTEGRATION DIRECTIVES

The game requires AAA console-level quality assets. Since direct 3D generation from text is a multi-step process, **Gemini and Claude must generate the exact procedural code, shader graphs, or Midjourney/Luma AI prompts** needed to create these, while **Copilot writes the Unity Editor scripts to auto-import and rig them.**

### A. Core Character & Animation Requirements
*   **Player Rig:** High-poly First-Person arms and weapon models.
*   **Animations:** 
    *   Smooth locomotion (Walk, Sprint, G-Slide transition, Bunny Hop landing impact).
    *   Tactical weapon handling (Equip, ADS, Hip-fire recoil, Tactical Reload, Empty Reload).
*   *Integration Directive:* Copilot, provide the exact Animator Controller state machine setup (JSON or C# builder script) to blend these animations flawlessly.

### B. Enemy Factions (The Pools)
*   **Zombies/Cryptids:** High-detail, optimized meshes with LODs (Level of Detail).
*   **Animations:** Spawn (crawling out), Walk, Sprint, Attack, Stagger, Death (Ragdoll or baked death animations).
*   *Integration Directive:* Claude, ensure `NeonPooler.cs` is configured to handle 50+ of these entities simultaneously without GC spikes.

### C. The Five Map Themes (Visual Fidelity Requirements)
For each map, generate the defining environmental assets, lighting profiles, and Post-Processing volumes.

1.  **Spaceland (UFO):** 
    *   *Aesthetic:* 1980s retro-futuristic theme park. Neon lights, chrome, volumetric fog.
    *   *Key Assets:* Flying UFO skybox element, arcade machines, laser-burn decals.
2.  **Rave (Vision):** 
    *   *Aesthetic:* 1990s deep woods rave. Blacklights, hallucinogenic post-processing, heavy particle effects.
    *   *Key Assets:* Turntables, glowing flora, reactive audio-visualizers.
3.  **Shaolin (Chi):** 
    *   *Aesthetic:* 1970s gritty New York meets Kung Fu cinema. Grimy textures, martial arts dojos, neon signs.
    *   *Key Assets:* Nunchaku weapon models, subway entrances, chi-energy VFX shaders.
4.  **Radioactive (Chemistry):** 
    *   *Aesthetic:* 1950s seaside town post-meltdown. Desaturated colors, glowing toxic green pools.
    *   *Key Assets:* Hazmat zombies, atomic bomb props, radiation distortion screen shaders.
5.  **Beast (Cryptids):** 
    *   *Aesthetic:* Deep space/alien dimension. Organic, HR Giger-inspired architecture.
    *   *Key Assets:* Cryptid enemy models, fleshy environmental textures, pulsating spore VFX.

---

## 4. IMMEDIATE ACTION PLAN FOR ALL AGENTS

**Step 1: Code Review & Hardening (Claude)**
Review the existing scripts in `C:\Users\Andrew Price\NEONPROTOCOL\Assets\Scripts`. Refactor `NeonMovement.cs` to guarantee the G-Slide feels exactly like Infinite Warfare. Ensure `NeonInputHandler.cs` is perfectly mapped for Android touch controls.

**Step 2: Asset Generation Strategy (Gemini)**
Output the exact procedural generation scripts (e.g., Unity Python/C# Editor scripts for generating primitive proxy shapes with complex shaders) OR output the precise prompts needed for external AI tools to generate the high-poly models, textures, and HDRI skyboxes for the Five Map Themes.

**Step 3: The Assembly Pipeline (Copilot)**
Write an `EditorWindow` C# script named `NeonAssetImporter.cs`. This script must automatically take imported models and textures, assign them the correct URP mobile shaders, configure their LOD groups, and attach them to the `NeonPooler` prefabs.

**Step 4: The Build (Copilot & Claude)**
Configure the `ProjectSettings` for Android deployment. Set the keystore parameters, optimize the IL2CPP build settings, and output the final instructions for compiling the `.apk`.

---
**[EXECUTION START]**
Acknowledge this master prompt. Output your assigned step and begin immediate execution. No placeholders. No theoretical advice. Generate the production-ready code and integration logic now.