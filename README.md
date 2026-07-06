# AI Hand-Gesture-Virtual-Mouse

![Python](https://img.shields.io/badge/Python-3.10-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

This project enables users to control their computer using hand gestures detected through a webcam.

The system tracks hand landmarks in real time and translates different gestures into mouse actions like cursor movement, clicking, dragging, scrolling, and volume control.

## ✨ Features

- Real-time hand tracking
- Cursor movement
- Left click
- Right click
- Drag & Drop
- Smooth cursor movement using One Euro Filter
- Scroll with momentum
- Volume Up
- Volume Down
- Gesture Debouncing
- Auto pinch calibration
- Interactive gesture visualization

## 🛠 Tech Stack
- Python
- OpenCV
- cvzone
- MediaPipe
- NumPy
- PyAutoGUI

## Installation

```bash
git clone https://github.com/nandinijha9939-dot/Hand-Gesture-Virtual-Mouse.git
```

```bash
cd Hand-Gesture-Virtual-Mouse
```

```bash
pip install -r requirements.txt
```

```bash
python hand_gesture_mouse.py
```

## 🎮 Gesture Controls

| Gesture | Action |
|----------|--------|
| Open Hand | Move Cursor |
| Pinch | Left Click |
| Pinch & Hold | Drag |
| Fist | Right Click |
| Two Fingers Up | Scroll Up |
| Two Fingers Down | Scroll Down |
| Three Fingers | Middle Click |
| Thumb Up | Volume Up |
| Thumb Down | Volume Down |

## ⌨️ Keyboard Shortcuts

| Key | Function |
|-----|----------|
| Q | Quit |
| R | Reset |
| F | Full Screen |

## ⭐ Highlights
- One Euro Filter for smooth cursor movement
- Gesture debouncing to reduce false detections
- Momentum-based scrolling
- Dynamic pinch threshold calibration
- Interactive neural-style hand visualization

## 🚀 Future Improvements
- Multi-hand support
- Brightness control
- Zoom gestures
- Custom gesture training
- Virtual keyboard

# output
###Cursor movement
<img width="637" height="513" alt="Screenshot 2026-07-06 133622" src="https://github.com/user-attachments/assets/04530dd1-6de8-4515-bb66-6e6f4f4e22a3" />
###Volume Up
<img width="648" height="506" alt="Screenshot 2026-07-06 133852" src="https://github.com/user-attachments/assets/de09e1b5-9c68-4e2e-a7b4-1ad102295eef" />

