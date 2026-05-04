# RealMathUniverse v0.4B1 Metal Keydown Hotfix

## Fix

The v0.4B Swift build failed because `AppDelegate` tried to override `keyDown`,
but `NSApplicationDelegate` does not inherit from `NSResponder`.

v0.4B1 fixes that by:

```text
- removing `override func keyDown` from AppDelegate
- using KeyCatcherWindow as the actual NSWindow subclass
- routing key events from KeyCatcherWindow to AppDelegate.handleKey()
- adding ImageIO import for screenshot writing
```

## Build

```bash
cd /Users/Joe/Documents/RealMathUniverse/metal_renderer
swift build -c release
```

## Run

```bash
swift run -c release RealMathUniverseMetalRenderer --project-root /Users/Joe/Documents/RealMathUniverse --size 1920x1080 --always-on-top
```
