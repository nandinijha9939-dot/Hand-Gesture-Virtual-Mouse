import cv2
import cvzone
from cvzone.HandTrackingModule import HandDetector
import pyautogui
import numpy as np
import math
import time
from collections import deque

# ============ PYAUTOGUI SPEED FIX ============
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0

# ============ CAMERA SETTINGS ============
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

detector = HandDetector(detectionCon=0.7, maxHands=1)
screen_w, screen_h = pyautogui.size()

print(f"Screen: {screen_w}x{screen_h}")


# ================================================================
# grade cursor smoothing
# ================================================================
class OneEuroFilter:
    def __init__(self, freq=30.0, mincutoff=1.2, beta=0.02, dcutoff=1.0):
        self.freq = freq
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def _alpha(self, cutoff):
        te = 1.0 / self.freq
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / te)

    def __call__(self, x, t=None):
        t = t if t is not None else time.time()

        if self.x_prev is None:
            self.x_prev = x
            self.t_prev = t
            return x

        te = max(t - self.t_prev, 1e-3)
        self.freq = 1.0 / te

        dx = (x - self.x_prev) / te
        a_d = self._alpha(self.dcutoff)
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev

        cutoff = self.mincutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff)
        x_hat = a * x + (1 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat


filter_x = OneEuroFilter(mincutoff=1.2, beta=0.015)
filter_y = OneEuroFilter(mincutoff=1.2, beta=0.015)
smooth_x, smooth_y = screen_w // 2, screen_h // 2


# ================================================================
# SCROLL CONTROLLER WITH MOMENTUM
# ================================================================
class ScrollController:
    def __init__(self):
        self.velocity = 0
        self.acceleration = 1.5
        self.friction = 0.85
        self.min_scroll = 5
        self.max_scroll = 80
        
    def scroll(self, direction):
        """Apply scroll with momentum"""
        self.velocity += direction * self.acceleration
        self.velocity = max(-self.max_scroll, min(self.max_scroll, self.velocity))
        
        # Apply scroll
        scroll_amount = int(self.velocity)
        if abs(scroll_amount) > self.min_scroll:
            pyautogui.scroll(scroll_amount)
        
        # Apply friction
        self.velocity *= self.friction
        if abs(self.velocity) < 0.5:
            self.velocity = 0
            
        return int(self.velocity)

scroll_controller = ScrollController()


# ================================================================
# GESTURE STATE
# ================================================================
class GestureState:
    def __init__(self):
        self.current = "Ready"
        self.previous = "Ready"
        self.transition_time = 0
        self.display_time = 0
        self.cooldown = 0
        self.is_dragging = False
        self.click_cooldown = 0
        self.scroll_cooldown = 0
        
    def update(self, new_gesture):
        if new_gesture != self.current:
            self.previous = self.current
            self.current = new_gesture
            self.transition_time = time.time()
            self.display_time = time.time()
        return self.current
    
    def should_show(self):
        return time.time() - self.display_time < 1.5

state = GestureState()

# Gesture debouncing
GESTURE_HOLD_FRAMES = 3
gesture_history = deque(maxlen=GESTURE_HOLD_FRAMES)
active_gesture = None

# ============ GESTURE THRESHOLDS ============
PINCH_THRESHOLD = 0.35
DRAG_THRESHOLD = 0.45
SCROLL_SPEED = 40
COOLDOWN_FRAMES = 8
FRAME_MARGIN = 0.15
VOLUME_COOLDOWN = 0


# ================================================================
# HELPER FUNCTIONS
# ================================================================

def count_fingers_up(landmarks):
    fingers = []
    fingers.append(1 if landmarks[4][0] > landmarks[3][0] else 0)
    fingers.append(1 if landmarks[8][1] < landmarks[6][1] else 0)
    fingers.append(1 if landmarks[12][1] < landmarks[10][1] else 0)
    fingers.append(1 if landmarks[16][1] < landmarks[14][1] else 0)
    fingers.append(1 if landmarks[20][1] < landmarks[18][1] else 0)
    return fingers

def get_palm_center(lmList):
    """Average of wrist + finger-base knuckles for stability"""
    idxs = [0, 5, 9, 13, 17]
    xs = [lmList[i][0] for i in idxs]
    ys = [lmList[i][1] for i in idxs]
    return sum(xs) / len(xs), sum(ys) / len(ys)

def map_to_screen(px, py, w, h):
    """Map camera-space to screen-space with margins"""
    mx, my = w * FRAME_MARGIN, h * FRAME_MARGIN
    nx = (px - mx) / (w - 2 * mx)
    ny = (py - my) / (h - 2 * my)
    nx = min(max(nx, 0.0), 1.0)
    ny = min(max(ny, 0.0), 1.0)
    return nx * screen_w, ny * screen_h

def move_cursor(px, py, w, h):
    """Unified cursor movement with One Euro filter"""
    global smooth_x, smooth_y
    tx, ty = map_to_screen(px, py, w, h)
    now = time.time()
    smooth_x = filter_x(tx, now)
    smooth_y = filter_y(ty, now)
    pyautogui.moveTo(int(smooth_x), int(smooth_y), _pause=False)

def debounce_gesture(candidate):
    """Require same gesture for multiple frames before committing"""
    global active_gesture
    gesture_history.append(candidate)
    if len(gesture_history) == GESTURE_HOLD_FRAMES and len(set(gesture_history)) == 1:
        active_gesture = candidate
    return active_gesture if active_gesture is not None else candidate

def calibrate_pinch(hand_size):
    """Auto-calibrate pinch threshold based on hand size"""
    base_threshold = 0.35
    return base_threshold * (1 + (hand_size - 100) / 1000)


# ================================================================
# VISUALIZATION FUNCTIONS
# ================================================================

def draw_neural_style(frame, landmarks, fingers_up, gesture):
    """Draw neural network style hand visualization"""
    if not landmarks:
        return frame

    connections = [
        (0, 5), (0, 9), (0, 13), (0, 17),
        (1, 2), (2, 3), (3, 4),
        (5, 6), (6, 7), (7, 8),
        (9, 10), (10, 11), (11, 12),
        (13, 14), (14, 15), (15, 16),
        (17, 18), (18, 19), (19, 20),
        (5, 9), (9, 13), (13, 17)
    ]

    # Draw glowing connections
    for start_idx, end_idx in connections:
        if start_idx < len(landmarks) and end_idx < len(landmarks):
            start = (landmarks[start_idx][0], landmarks[start_idx][1])
            end = (landmarks[end_idx][0], landmarks[end_idx][1])
            dist = math.dist(start, end)
            intensity = max(0.2, 1 - dist / 250)
            cv2.line(frame, start, end,
                     (int(50 * intensity), int(200 * intensity), int(150 * intensity)),
                     max(1, int(2 * intensity)))

    # Draw glowing nodes
    for i, point in enumerate(landmarks):
        x, y = point[0], point[1]
        if i == 0:
            color = (0, 255, 255)
            radius = 8
        elif i in [4, 8, 12, 16, 20]:
            idx = [4, 8, 12, 16, 20].index(i)
            if idx < len(fingers_up) and fingers_up[idx]:
                color = (0, 255, 0)
                radius = 7
            else:
                color = (50, 50, 50)
                radius = 5
        else:
            color = (0, 200, 255)
            radius = 6

        # Glow effect
        for r in range(15, 0, -3):
            alpha = r / 15
            glow = (int(color[0] * alpha * 0.3), 
                    int(color[1] * alpha * 0.3), 
                    int(color[2] * alpha * 0.3))
            cv2.circle(frame, (x, y), r, glow, -1)

        cv2.circle(frame, (x, y), radius, color, -1)
        cv2.circle(frame, (x, y), radius + 1, (255, 255, 255), 1)

    return frame

def draw_gesture_transition(frame, old_gesture, new_gesture, transition_time):
    """Smooth gesture transition with animation"""
    h, w, _ = frame.shape
    
    # Show big gesture name when transitioning
    elapsed = time.time() - transition_time
    if elapsed < 1.0:
        alpha = 1 - elapsed
        if old_gesture != new_gesture and alpha > 0.3:
            # Fade out old gesture
            cv2.putText(frame, f"← {old_gesture}", (w//2-150, h//2-50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, 
                       (int(255*alpha), int(100*alpha), int(100*alpha)), 2)
        
        # Fade in new gesture
        if elapsed > 0.2:
            fade = min(1, (elapsed - 0.2) / 0.3)
            cv2.putText(frame, f"→ {new_gesture}", (w//2-150, h//2+20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                       (int(0*fade), int(255*fade), int(100*fade)), 2)
    
    return frame

def draw_big_gesture_alert(frame, gesture, start_time):
    """Show large gesture alert for important actions"""
    h, w, _ = frame.shape
    elapsed = time.time() - start_time
    
    if elapsed < 1.0 and gesture in ["Click", "Right Click", "Scroll Up", "Scroll Down"]:
        alpha = 1 - elapsed
        # Large semi-transparent gesture display
        overlay = frame.copy()
        text = gesture.upper()
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 2, 4)
        x = w//2 - tw//2
        y = h//2 - th//2
        
        # Background
        cv2.rectangle(overlay, (x-30, y-20), (x+tw+30, y+th+20), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.3 * alpha, frame, 0.7 * (1 - alpha), 0, frame)
        
        # Glowing text
        color = (int(0*alpha), int(255*alpha), int(100*alpha))
        cv2.putText(frame, text, (x, y+th), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, color, 4)
        
        # Glow effect
        for i in range(3):
            alpha2 = (3 - i) / 10 * alpha
            glow_color = (int(0*alpha2), int(255*alpha2), int(100*alpha2))
            cv2.putText(frame, text, (x+i*2, y+th+i*2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, glow_color, 2)
    
    return frame

def draw_info_panel(frame, gesture, fingers_up, is_dragging, scroll_velocity):
    """Enhanced information panel with more details"""
    h, w, _ = frame.shape
    panel = np.zeros((150, 300, 3), dtype=np.uint8)
    panel[:] = (0, 0, 0)
    cv2.rectangle(panel, (0, 0), (panel.shape[1] - 1, panel.shape[0] - 1), 
                  (0, 200, 150), 1)
    frame[10:160, 10:310] = panel

    # Title with animation
    pulse = 0.5 + 0.5 * math.sin(time.time() * 2)
    cv2.putText(frame, "🧠 NEURAL HAND", (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                (int(0*pulse), int(255*pulse), int(255*pulse)), 1)
    
    # Gesture name with color
    gesture_color = (0, 255, 0) if gesture not in ["Ready", "No Hand"] else (200, 200, 200)
    cv2.putText(frame, f"Gesture: {gesture}", (20, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, gesture_color, 1)

    # Finger activation bar with gradient
    finger_count = sum(fingers_up) if fingers_up else 0
    bar_width = int((finger_count / 5) * 180)
    cv2.rectangle(frame, (20, 80), (20 + 180, 90), (40, 40, 40), -1)
    cv2.rectangle(frame, (20, 80), (20 + bar_width, 90), (0, 255, 0), -1)
    cv2.putText(frame, f"Fingers: {finger_count}/5", (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

    # Status with pulsing
    status = "DRAGGING" if is_dragging else "READY"
    color = (0, 255, 255) if is_dragging else (0, 255, 0)
    cv2.putText(frame, f"Status: {status}", (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Scroll velocity indicator
    if scroll_velocity != 0:
        cv2.putText(frame, f"Scroll: {scroll_velocity}", (20, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

    return frame

def draw_finger_indicators(frame, fingers_up):
    """Visual finger status indicators"""
    if not fingers_up:
        return frame
    
    h, w, _ = frame.shape
    x_start = w - 70
    y_start = 30
    
    finger_icons = ["👍", "👆", "🖕", "🖖", "🤙"]
    finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
    
    for i, (icon, is_up, name) in enumerate(zip(finger_icons, fingers_up, finger_names)):
        y = y_start + i * 28
        color = (0, 255, 0) if is_up else (50, 50, 50)
        cv2.putText(frame, icon, (x_start, y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Small indicator dot
        cv2.circle(frame, (x_start + 35, y + 10), 4, color, -1)
    
    return frame

def draw_performance_metrics(frame, fps, smoothing_values):
    """Draw performance metrics"""
    h, w, _ = frame.shape
    
    # FPS and smoothing info
    cv2.putText(frame, f"FPS: {fps}", (w - 100, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    
    # Show smoothing values
    cv2.putText(frame, f"Smooth: {smoothing_values[0]:.1f}, {smoothing_values[1]:.1f}", 
                (w - 200, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)
    
    return frame


# ================================================================
# MAIN LOOP
# ================================================================

print("""
╔══════════════════════════════════════════════════════════════════╗
║      GESTURE CONTROL ✋                          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ✋ Open Hand         → Move Mouse                              ║
║  👌 Pinch             → Left Click                              ║
║  🤏 Pinch & Hold      → Drag                                    ║
║  ✊ Fist              → Right Click                             ║
║  ✌️ Two Up            → Scroll Up (with momentum)               ║
║  👇 Two Down          → Scroll Down (with momentum)             ║
║  🖐️ Three Up          → Middle Click                            ║
║  👍 Thumbs Up         → Volume Up                               ║
║  👎 Thumbs Down       → Volume Down                             ║
║                                                                  ║
║  Press 'q' → Quit  │  'r' → Reset  │  'f' → Full Screen          ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")

frame_count = 0
fps_time = time.time()
fps_display = "30"
smooth_display = (0, 0)

# Variables for gesture transition
last_gesture_name = "Ready"
transition_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    hands, frame = detector.findHands(frame, draw=False)

    if not hands:
        if state.is_dragging:
            pyautogui.mouseUp()
            state.is_dragging = False
        gesture_history.clear()
        active_gesture = None
        last_gesture_name = "No Hand"
        
        frame = draw_neural_style(frame, None, None, last_gesture_name)
        cv2.putText(frame, "Show your hand", (w // 2 - 100, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow('Gesture Control', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue

    # ============ GET HAND DATA ============
    hand = hands[0]
    lmList = hand['lmList']
    bbox = hand['bbox']
    hand_size = max(bbox[2], bbox[3], 1)

    fingers_up = count_fingers_up(lmList)
    finger_count = sum(fingers_up)

    palm_x, palm_y = get_palm_center(lmList)
    thumb = lmList[4]
    index = lmList[8]
    middle = lmList[12]

    # Normalized distances
    pinch_dist_norm = math.dist((thumb[0], thumb[1]), (index[0], index[1])) / hand_size
    thumb_index_dist = math.dist((thumb[0], thumb[1]), (index[0], index[1]))

    # ============ COOLDOWNS ============
    if state.click_cooldown > 0:
        state.click_cooldown -= 1
    if state.scroll_cooldown > 0:
        state.scroll_cooldown -= 1
    if VOLUME_COOLDOWN > 0:
        VOLUME_COOLDOWN -= 1

    # ============ AUTO-CALIBRATION ============
    dynamic_pinch_threshold = calibrate_pinch(hand_size)

    # ============ GESTURE DETECTION ============
    candidate = "unknown"

    # 1. OPEN HAND - Move
    if finger_count >= 4:
        candidate = "move"
    
    # 2. THUMBS UP - Volume Up
    elif fingers_up[0] == 1 and sum(fingers_up[1:]) == 0 and thumb_index_dist > 50:
        if VOLUME_COOLDOWN == 0:
            pyautogui.press('volumeup')
            VOLUME_COOLDOWN = 15
            candidate = "volume_up"
            state.update("Volume Up")
        else:
            candidate = "volume_up"
    
    # 3. THUMBS DOWN - Volume Down
    elif fingers_up[0] == 0 and sum(fingers_up[1:]) == 0 and fingers_up[0] == 0:
        # Thumb down detection - all fingers closed, thumb pointing down
        if VOLUME_COOLDOWN == 0:
            pyautogui.press('volumedown')
            VOLUME_COOLDOWN = 15
            candidate = "volume_down"
            state.update("Volume Down")
        else:
            candidate = "volume_down"
    
    # 4. PINCH - Click
    elif pinch_dist_norm < dynamic_pinch_threshold and finger_count <= 2:
        candidate = "click"
    
    # 5. PINCH & HOLD - Drag
    elif pinch_dist_norm < DRAG_THRESHOLD and finger_count <= 2:
        candidate = "drag"
    
    # 6. FIST - Right Click
    elif finger_count == 0:
        candidate = "right_click"
    
    # 7. TWO FINGERS UP - Scroll Up
    elif finger_count == 2 and fingers_up[1] == 1 and fingers_up[2] == 1 and fingers_up[0] == 0:
        candidate = "scroll_up"
    
    # 8. TWO FINGERS DOWN - Scroll Down
    elif finger_count == 2 and fingers_up[1] == 0 and fingers_up[2] == 0 and fingers_up[0] == 0:
        candidate = "scroll_down"
    
    # 9. THREE FINGERS - Middle Click
    elif finger_count == 3:
        candidate = "middle_click"

    # ============ DEBOUNCE DISCRETE GESTURES ============
    if candidate in ("move", "drag"):
        gesture_history.clear()
        active_gesture = None
        gesture = candidate
    else:
        gesture = debounce_gesture(candidate)

    gesture_triggered = False
    scroll_velocity = 0

    # ============ EXECUTE GESTURE ============
    if gesture == "move":
        move_cursor(palm_x, palm_y, w, h)
        gesture_name = "Moving"
        gesture_triggered = True
        if state.is_dragging:
            pyautogui.mouseUp()
            state.is_dragging = False

    elif gesture == "click":
        if state.click_cooldown == 0:
            pyautogui.click()
            state.click_cooldown = COOLDOWN_FRAMES
            gesture_triggered = True
            state.update("Click")
            transition_time = time.time()
        gesture_name = "Click"
        if state.is_dragging:
            pyautogui.mouseUp()
            state.is_dragging = False

    elif gesture == "drag":
        if not state.is_dragging:
            pyautogui.mouseDown()
            state.is_dragging = True
            gesture_triggered = True
            state.update("Drag Start")
            transition_time = time.time()
        move_cursor(palm_x, palm_y, w, h)
        gesture_name = "Dragging"

    elif gesture == "right_click":
        if state.click_cooldown == 0:
            pyautogui.rightClick()
            state.click_cooldown = COOLDOWN_FRAMES
            gesture_triggered = True
            state.update("Right Click")
            transition_time = time.time()
        gesture_name = "Right Click"
        if state.is_dragging:
            pyautogui.mouseUp()
            state.is_dragging = False

    elif gesture == "scroll_up":
        if state.scroll_cooldown == 0:
            scroll_velocity = scroll_controller.scroll(1)
            state.scroll_cooldown = COOLDOWN_FRAMES
            gesture_triggered = True
            state.update("Scroll Up")
            transition_time = time.time()
        gesture_name = "Scroll Up"
        if state.is_dragging:
            pyautogui.mouseUp()
            state.is_dragging = False

    elif gesture == "scroll_down":
        if state.scroll_cooldown == 0:
            scroll_velocity = scroll_controller.scroll(-1)
            state.scroll_cooldown = COOLDOWN_FRAMES
            gesture_triggered = True
            state.update("Scroll Down")
            transition_time = time.time()
        gesture_name = "Scroll Down"
        if state.is_dragging:
            pyautogui.mouseUp()
            state.is_dragging = False

    elif gesture == "middle_click":
        if state.click_cooldown == 0:
            pyautogui.middleClick()
            state.click_cooldown = COOLDOWN_FRAMES
            gesture_triggered = True
            state.update("Middle Click")
            transition_time = time.time()
        gesture_name = "Middle Click"
        if state.is_dragging:
            pyautogui.mouseUp()
            state.is_dragging = False

    elif gesture == "volume_up":
        gesture_name = "Volume Up"
        gesture_triggered = True

    elif gesture == "volume_down":
        gesture_name = "Volume Down"
        gesture_triggered = True

    else:
        if state.is_dragging:
            pyautogui.mouseUp()
            state.is_dragging = False
        gesture_name = f"{finger_count} Fingers"

    # Update gesture display
    if gesture_triggered:
        last_gesture_name = gesture_name
        state.display_time = time.time()

    if time.time() - state.display_time > 1.5 and gesture_name not in ["Moving", "Dragging"]:
        last_gesture_name = "Dragging" if state.is_dragging else "Ready"

    # ============ VISUALIZATION ============
    
    # Draw neural style hand
    frame = draw_neural_style(frame, lmList, fingers_up, last_gesture_name)
    
    # Draw gesture transition animation
    frame = draw_gesture_transition(frame, state.previous, last_gesture_name, transition_time)
    
    # Draw big gesture alert
    frame = draw_big_gesture_alert(frame, last_gesture_name, transition_time)
    
    # Draw info panel
    frame = draw_info_panel(frame, last_gesture_name, fingers_up, 
                           state.is_dragging, scroll_velocity)
    
    # Draw finger indicators
    frame = draw_finger_indicators(frame, fingers_up)
    
    # Show drag indicator
    if state.is_dragging:
        cv2.putText(frame, "🔴 DRAGGING", (w - 130, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # Mouse position
    cv2.putText(frame, f"Mouse: ({int(smooth_x)}, {int(smooth_y)})", (w - 220, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

    # ============ PERFORMANCE METRICS ============
    frame_count += 1
    if time.time() - fps_time > 1:
        fps_display = str(frame_count)
        frame_count = 0
        fps_time = time.time()
    
    smooth_display = (smooth_x, smooth_y)
    frame = draw_performance_metrics(frame, fps_display, smooth_display)

    # Show frame
    cv2.imshow('Gesture Control', frame)

    # ============ KEYBOARD CONTROLS ============
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('f'):
        cv2.setWindowProperty('Gesture Control', 
                            cv2.WND_PROP_FULLSCREEN, 
                            cv2.WINDOW_FULLSCREEN)
    elif key == ord('r'):
        smooth_x, smooth_y = screen_w // 2, screen_h // 2
        filter_x.x_prev = None
        filter_y.x_prev = None
        state.is_dragging = False
        state.click_cooldown = 0
        state.scroll_cooldown = 0
        scroll_controller.velocity = 0
        gesture_history.clear()
        active_gesture = None
        last_gesture_name = "Ready"
        state.current = "Ready"
        print("🔄 Reset complete!")

cap.release()
cv2.destroyAllWindows()