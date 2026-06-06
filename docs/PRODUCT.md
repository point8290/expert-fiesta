# Product Document: Local AI Music Video Generation Pipeline

## 1. Product Name

- **Working Name:** Local Music Video Studio
- **Alternative Names:** AI Music Video Lab, LocalMV, StorySong Studio

---

## 2. Product Vision

Build a local-first AI-powered system that allows a creator to generate an
original song concept, lyrics, storyboard, character references, animated video
clips, and a final stitched music video using mostly local models and
open-source tools.

The product should help users create music-video-style animated content without
depending heavily on expensive cloud APIs.

---

## 3. Core Problem

Creating animated music videos is expensive, slow, and requires multiple skills:

- Songwriting
- Storyboarding
- Character design
- Animation
- Video editing
- Audio-video synchronization
- Rendering

AI tools can help, but most workflows are fragmented. Users currently need to
manually move between many tools such as music generators, image generators,
video generators, editors, and file managers.

This product solves that by creating a single local pipeline where each step is
organized, repeatable, and scene-based.

---

## 4. Target Users

### Primary Users

1. Independent musicians
2. YouTube creators
3. AI content creators
4. Short film/music video experimenters
5. Developers building AI creative tools

### Secondary Users

1. Marketing creators
2. Indie game storytellers
3. Animation hobbyists
4. Social media creators

---

## 5. Main Use Case

A user enters an idea like:

> "Create an emotional animated pop-rock music video about two childhood
> friends, memories, birds, and growing apart."

The system generates:

1. Song title
2. Lyrics
3. Music generation prompt
4. Story concept
5. Character descriptions
6. Scene-by-scene storyboard
7. Character reference images
8. Scene keyframes
9. Short animated clips
10. Final MP4 music video

---

## 6. Product Scope

### MVP Scope

The MVP should generate a 40–60 second local-first animated music video.

**MVP input:**

- Song idea
- Genre
- Mood
- Visual style
- Target duration
- Optional uploaded audio

**MVP output:**

- Lyrics
- Music prompt
- Storyboard
- Character descriptions
- 8–12 scene prompts
- Keyframe images
- 5-second video clips
- Final stitched MP4

---

## 7. MVP Features

### 7.1 Project Creation

User can create a new music video project.

Fields:

- Project title
- Song idea
- Genre
- Mood
- Visual style
- Target duration
- Aspect ratio

Example:

```json
{
  "title": "Wings We Leave Behind",
  "idea": "A story about childhood friends, memories, and birds",
  "genre": "cinematic pop rock",
  "mood": "bittersweet and uplifting",
  "visualStyle": "2D hand-painted animation",
  "targetDuration": 60,
  "aspectRatio": "16:9"
}
```

### 7.2 Lyrics and Song Prompt Generation

The system uses a local LLM to generate:

- Song title
- Lyrics
- Song structure
- Music generation prompt
- Emotional arc

The system must avoid copying existing songs, artists, lyrics, melodies, or
music videos.

### 7.3 Audio Input

The MVP should support two options:

1. **Manual audio upload**
   - User uploads MP3/WAV generated elsewhere.
   - This should be the first implementation.
2. **Local song generation**
   - Later integration with ACE-Step or another local music generation model.

Manual upload should be prioritized because it keeps the MVP simple and avoids
early complexity.

### 7.4 Audio Analysis

The system analyzes uploaded audio and extracts:

- Duration
- Estimated BPM
- Rough sections
- Beat timestamps
- Waveform data

This helps generate scene timing.

### 7.5 Storyboard Generation

The system generates a scene-by-scene storyboard.

Each scene includes:

- Scene number
- Start time
- End time
- Duration
- Section name
- Visual description
- Camera instruction
- Motion instruction
- Keyframe prompt
- Video prompt
- Negative prompt

Example:

```json
{
  "sceneNumber": 1,
  "startTime": 0,
  "endTime": 5,
  "durationSeconds": 5,
  "sectionName": "intro",
  "visualDescription": "Two children sit on a rooftop at sunset, watching birds cross the sky.",
  "cameraInstruction": "Slow cinematic push-in",
  "motionInstruction": "Birds drift slowly across the warm orange sky",
  "keyframePrompt": "2D hand-painted animated scene, two children on rooftop at sunset...",
  "videoPrompt": "Slow push-in, gentle wind, birds flying in distance...",
  "negativePrompt": "deformed faces, extra limbs, flickering, text, watermark"
}
```

### 7.6 Character Bible

The system generates a character bible for consistency.

Each character should have:

- Name
- Age
- Face description
- Hair
- Clothing
- Personality
- Identity anchors
- Reference image path

Example:

```json
{
  "id": "child_a",
  "name": "Aarav",
  "age": "10",
  "face": "round face, expressive brown eyes",
  "hair": "messy black hair",
  "clothing": "yellow hoodie",
  "identityAnchors": [
    "yellow hoodie",
    "messy black hair",
    "round face",
    "brown eyes"
  ]
}
```

### 7.7 Keyframe Generation

For each scene, the system generates one keyframe image using ComfyUI.

The keyframe should act as the visual anchor for video generation.

The user should be able to:

- View keyframe
- Approve keyframe
- Regenerate keyframe
- Edit prompt
- Replace keyframe manually

### 7.8 Scene Video Generation

For each approved keyframe, the system generates a short video clip.

Recommended MVP duration:

- 5 seconds per scene
- 8–12 scenes per project
- 40–60 seconds total

The system should generate video scene-by-scene, not as one long video.

The user should be able to:

- Preview clip
- Approve clip
- Regenerate clip
- Upload replacement clip
- Mark scene as final

### 7.9 Final Video Rendering

The system stitches all approved clips into a final music video using FFmpeg.

Final render includes:

- Normalized clip resolution
- Normalized frame rate
- Ordered scene stitching
- Added song audio
- Exported MP4

MVP can use hard cuts first. Crossfades and transitions can be added later.

---

## 8. Non-MVP Features

These should not be built first.

### Later Features

1. Local full-song generation
2. Advanced timeline editor
3. Crossfade transition editor
4. Beat-synced cuts
5. Automatic subtitle/lyrics overlay
6. Multiple video model support
7. Cloud fallback for difficult scenes
8. Quality scoring
9. Character consistency scoring
10. Multi-user support
11. SaaS billing
12. Project export/import
13. Version history
14. Shot comparison view
15. Prompt library

---

## 9. User Flow

### MVP Flow

1. User creates project
2. User enters song idea
3. System generates lyrics and music prompt
4. User uploads audio
5. System analyzes audio
6. System generates storyboard
7. User reviews storyboard
8. System generates character references
9. User approves characters
10. System generates keyframes
11. User approves keyframes
12. System generates video clips
13. User approves clips
14. System renders final MP4
15. User downloads final video

---

## 10. Product Screens

### 10.1 Dashboard

Shows all projects. Each project card shows:

- Title
- Status
- Duration
- Created date
- Last modified date
- Thumbnail

### 10.2 Project Creation Screen

Fields: Title, Idea, Genre, Mood, Visual style, Duration, Aspect ratio.
Button: Create Project.

### 10.3 Lyrics Screen

Shows: Generated title, Lyrics, Music prompt, Regenerate button, Save button.

### 10.4 Audio Screen

Allows: Upload audio, Preview audio, View duration, View waveform, Analyze audio.

### 10.5 Storyboard Screen

Shows all scenes as cards. Each scene card includes: Scene number, Time range,
Visual description, Prompt, Negative prompt, Regenerate prompt button.

### 10.6 Character Screen

Shows: Character descriptions, Character reference images, Regenerate reference
button, Approve button.

### 10.7 Keyframe Screen

Shows: Scene prompt, Generated keyframe, Approve button, Regenerate button.

### 10.8 Clip Generation Screen

Shows: Scene keyframe, Generated video clip, Clip status, Approve/regenerate
buttons.

### 10.9 Final Render Screen

Shows: All approved clips, Render button, Final video preview, Download MP4
button.

---

## 11. Success Metrics

### MVP Success Metrics

1. User can generate a complete 40–60 second video.
2. Final video is exported successfully as MP4.
3. At least 70% of scenes are usable after 1–3 generations.
4. User can regenerate bad scenes without restarting the full project.
5. Pipeline runs locally without paid APIs.

---

## 12. Constraints

### Technical Constraints

- Local video generation is slow.
- GPU VRAM limits output quality.
- Character consistency is difficult.
- Long videos should be avoided initially.
- ComfyUI workflow compatibility may break due to custom node updates.

### Product Constraints

- Must be scene-based.
- Must allow manual replacement of assets.
- Must not rely on one video model.
- Must allow user approval at every important stage.

---

## 13. Recommended MVP Definition

The first version should be:

> A local web app where a user enters a song idea, uploads audio, generates a
> storyboard, generates keyframes and 5-second video clips using ComfyUI, and
> exports a final 40–60 second MP4 using FFmpeg.

Do not start with full automation. Start with a controllable, reviewable,
scene-based workflow.

---

## 14. Product Roadmap (source)

- **Phase 1: Pipeline Skeleton** — Project creation, lyrics generation,
  storyboard generation, audio upload, scene management, manual clip upload,
  FFmpeg final render.
- **Phase 2: Local Image Generation** — ComfyUI integration, character
  references, scene keyframes, keyframe approval UI.
- **Phase 3: Local Video Generation** — LTX-Video integration, scene video
  generation, regenerate scene, final render with generated clips.
- **Phase 4: Better Quality** — Wan 2.2 workflow, HunyuanVideo workflow, prompt
  versioning, character consistency checks, transition options.
- **Phase 5: Productization** — Project templates, multi-user support, cloud
  fallback, usage tracking, export presets, optional SaaS version.

---

## 15. Product Positioning

This product is not a one-click professional music video generator.

It should be positioned as:

> A local AI-assisted music video production pipeline for creators who want
> control, privacy, low API cost, and scene-level editing.

The key value is not only generation, but organized creative control.
