# AI Hand-Gesture-Virtual-Mouse
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

## 🚀 Future Improvements
- Multi-hand support
- Brightness control
- Zoom gestures
- Custom gesture training
- Virtual keyboard

#some output gesture images

<img width="637" height="513" alt="Screenshot 2026-07-06 133622" src="https://github.com/user-attachments/assets/04530dd1-6de8-4515-bb66-6e6f4f4e22a3" />

<img width="637" height="513" alt="Screenshot 2026-07-06 133622" src="https://github.com/user-attachments/assets/88b48d97-13e9-444b-9288-01a98f0846e6" />

