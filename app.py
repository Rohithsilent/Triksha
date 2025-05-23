import streamlit as st
import cv2 as cv
import numpy as np
import mediapipe as mp
import copy
import itertools
from collections import Counter
from collections import deque
import time
import csv
import pyttsx3  # For offline text-to-speech
import threading  # For non-blocking speech

# Import your custom model classes
# Assuming these are in the same directory
from model import KeyPointClassifier
from model import PointHistoryClassifier

# Set page config
st.set_page_config(
    page_title="Triksha", 
    page_icon="👋", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title
st.title("Hand Gesture Recognition")

# Initialize session state variables
if 'camera_running' not in st.session_state:
    st.session_state.camera_running = False
if 'speech_enabled' not in st.session_state:
    st.session_state.speech_enabled = False
if 'last_spoken_gesture' not in st.session_state:
    st.session_state.last_spoken_gesture = ""
if 'speak_timestamp' not in st.session_state:
    st.session_state.speak_timestamp = 0

# Initialize text-to-speech engine
def initialize_tts_engine():
    engine = pyttsx3.init()
    # Configure the voice properties (optional)
    engine.setProperty('rate', 150)  # Speed of speech
    engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
    return engine

# Function to speak text in a non-blocking way
def speak_text(text):
    def speak_worker(text_to_speak):
        engine = initialize_tts_engine()
        engine.say(text_to_speak)
        engine.runAndWait()
    
    # Start speech in a separate thread to avoid blocking the UI
    thread = threading.Thread(target=speak_worker, args=(text,))
    thread.daemon = True
    thread.start()

# Sidebar for parameters
st.sidebar.header("Parameters")
detection_confidence = st.sidebar.slider("Detection Confidence", 0.5, 1.0, 0.7, 0.1)
tracking_confidence = st.sidebar.slider("Tracking Confidence", 0.5, 1.0, 0.5, 0.1)
use_brect = st.sidebar.checkbox("Show Bounding Rectangle", value=True)

# Speech settings
st.sidebar.header("Speech Settings")
speech_enabled = st.sidebar.checkbox("Enable Speech", value=st.session_state.speech_enabled)
speech_cooldown = st.sidebar.slider("Speech Cooldown (seconds)", 0.5, 5.0, 2.0, 0.1)

# Update speech state if changed
if speech_enabled != st.session_state.speech_enabled:
    st.session_state.speech_enabled = speech_enabled
    if speech_enabled:
        speak_text("Speech feedback enabled")

# Create a toggle button function
def toggle_camera():
    st.session_state.camera_running = not st.session_state.camera_running

def main():
    # Setup MediaPipe
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=detection_confidence,
        min_tracking_confidence=tracking_confidence,
    )

    # Load models
    keypoint_classifier = KeyPointClassifier()
    point_history_classifier = PointHistoryClassifier()

    # Read labels
    with open('model/keypoint_classifier/keypoint_classifier_label.csv',
              encoding='utf-8-sig') as f:
        keypoint_classifier_labels = [row[0] for row in csv.reader(f)]
        
    with open('model/point_history_classifier/point_history_classifier_label.csv',
              encoding='utf-8-sig') as f:
        point_history_classifier_labels = [row[0] for row in csv.reader(f)]

    # Coordinate history
    history_length = 16
    point_history = deque(maxlen=history_length)
    finger_gesture_history = deque(maxlen=history_length)

    # Mode
    mode = 0
    number = -1

    # FPS calculation
    prev_time = 0
    
    # Streamlit camera input
    camera_col, info_col = st.columns([3, 1])
    
    with camera_col:
        # Use Streamlit's camera input
        camera_placeholder = st.empty()
    
    with info_col:
        st.subheader("Instructions")
        st.write("- Press 'n' for normal mode")
        st.write("- Press 'k' for keypoint logging")
        st.write("- Press 'h' for point history logging")
        st.write("- Press 0-9 to input numbers for logging")
        
        # Display detected gesture
        gesture_placeholder = st.empty()
        fps_placeholder = st.empty()
        mode_placeholder = st.empty()
        
        # Speech status
        speech_status = st.empty()
        if st.session_state.speech_enabled:
            speech_status.success("Speech feedback is enabled")
        else:
            speech_status.info("Speech feedback is disabled")
    
    # Camera toggle button
    if st.button("Start Camera" if not st.session_state.camera_running else "Stop Camera"):
        st.session_state.camera_running = not st.session_state.camera_running
        st.rerun()

    # Start camera if running
    if st.session_state.camera_running:
        cap = cv.VideoCapture(0)
        cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)

        while st.session_state.camera_running:
            # Calculate FPS
            current_time = time.time()
            fps = 1 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
            prev_time = current_time
            fps_placeholder.write(f"FPS: {fps:.1f}")

            # Camera capture
            ret, image = cap.read()
            if not ret:
                break
            
            image = cv.flip(image, 1)  # Mirror display
            debug_image = copy.deepcopy(image)

            # Detection implementation
            image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = hands.process(image)
            image.flags.writeable = True

            current_gesture = "No hand detected"
            
            # Process results
            if results.multi_hand_landmarks is not None:
                for hand_landmarks, handedness in zip(results.multi_hand_landmarks,
                                                  results.multi_handedness):
                    # Bounding box calculation
                    brect = calc_bounding_rect(debug_image, hand_landmarks)
                    
                    # Landmark calculation
                    landmark_list = calc_landmark_list(debug_image, hand_landmarks)

                    # Conversion to relative coordinates / normalized coordinates
                    pre_processed_landmark_list = pre_process_landmark(landmark_list)
                    pre_processed_point_history_list = pre_process_point_history(
                        debug_image, point_history)

                    # Hand sign classification
                    hand_sign_id = keypoint_classifier(pre_processed_landmark_list)
                    if hand_sign_id == 2:  # Point gesture
                        point_history.append(landmark_list[8])
                    else:
                        point_history.append([0, 0])

                    # Finger gesture classification
                    finger_gesture_id = 0
                    point_history_len = len(pre_processed_point_history_list)
                    if point_history_len == (history_length * 2):
                        finger_gesture_id = point_history_classifier(
                            pre_processed_point_history_list)

                    # Calculates the gesture IDs in the latest detection
                    finger_gesture_history.append(finger_gesture_id)
                    most_common_fg_id = Counter(finger_gesture_history).most_common()

                    # Drawing part
                    debug_image = draw_bounding_rect(use_brect, debug_image, brect)
                    debug_image = draw_landmarks(debug_image, landmark_list)
                    debug_image = draw_info_text(
                        debug_image,
                        brect,
                        handedness,
                        keypoint_classifier_labels[hand_sign_id],
                        point_history_classifier_labels[most_common_fg_id[0][0]],
                    )
                    
                    # Prepare gesture text for display and speech
                    hand_type = handedness.classification[0].label[0:]
                    gesture_name = keypoint_classifier_labels[hand_sign_id]
                    finger_gesture = point_history_classifier_labels[most_common_fg_id[0][0]]
                    
                    gesture_text = f"Hand: {hand_type}\nGesture: {gesture_name}"
                    speech_text = f"{hand_type} hand, {gesture_name}"
                    
                    if most_common_fg_id[0][0] != 0:
                        gesture_text += f"\nFinger Gesture: {finger_gesture}"
                        speech_text += f", finger gesture {finger_gesture}"
                    
                    gesture_placeholder.write(gesture_text)
                    current_gesture = speech_text
            else:
                point_history.append([0, 0])
                gesture_placeholder.write("No hand detected")
                current_gesture = "No hand detected"

            # Speech output with cooldown to prevent constant speaking
            if (st.session_state.speech_enabled and 
                current_gesture != "No hand detected" and
                (current_gesture != st.session_state.last_spoken_gesture or 
                 time.time() - st.session_state.speak_timestamp > speech_cooldown)):
                speak_text(current_gesture)
                st.session_state.last_spoken_gesture = current_gesture
                st.session_state.speak_timestamp = time.time()

            debug_image = draw_point_history(debug_image, point_history)
            
            # Mode display
            mode_string = ['Normal', 'Logging Key Point', 'Logging Point History']
            if 0 <= mode <= 2:
                mode_text = f"Mode: {mode_string[mode]}"
                if 0 <= number <= 9 and mode > 0:
                    mode_text += f"\nNumber: {number}"
                mode_placeholder.write(mode_text)

            # Convert from BGR to RGB for Streamlit
            debug_image = cv.cvtColor(debug_image, cv.COLOR_BGR2RGB)
            
            # Display the image
            camera_placeholder.image(debug_image, channels="RGB", use_column_width=True)
        
        # Release resources when done
        cap.release()
        st.write("Camera stopped")
    else:
        # Display message when camera is off
        camera_placeholder.write("Camera is turned off. Click 'Start Camera' to begin.")


def calc_bounding_rect(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_array = np.empty((0, 2), int)

    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)

        landmark_point = [np.array((landmark_x, landmark_y))]

        landmark_array = np.append(landmark_array, landmark_point, axis=0)

    x, y, w, h = cv.boundingRect(landmark_array)

    return [x, y, x + w, y + h]


def calc_landmark_list(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_point = []

    # Keypoint
    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)

        landmark_point.append([landmark_x, landmark_y])

    return landmark_point


def pre_process_landmark(landmark_list):
    temp_landmark_list = copy.deepcopy(landmark_list)

    # Convert to relative coordinates
    base_x, base_y = 0, 0
    for index, landmark_point in enumerate(temp_landmark_list):
        if index == 0:
            base_x, base_y = landmark_point[0], landmark_point[1]

        temp_landmark_list[index][0] = temp_landmark_list[index][0] - base_x
        temp_landmark_list[index][1] = temp_landmark_list[index][1] - base_y

    # Convert to a one-dimensional list
    temp_landmark_list = list(
        itertools.chain.from_iterable(temp_landmark_list))

    # Normalization
    max_value = max(list(map(abs, temp_landmark_list)))

    def normalize_(n):
        return n / max_value

    temp_landmark_list = list(map(normalize_, temp_landmark_list))

    return temp_landmark_list


def pre_process_point_history(image, point_history):
    image_width, image_height = image.shape[1], image.shape[0]

    temp_point_history = copy.deepcopy(point_history)

    # Convert to relative coordinates
    base_x, base_y = 0, 0
    for index, point in enumerate(temp_point_history):
        if index == 0:
            base_x, base_y = point[0], point[1]

        temp_point_history[index][0] = (temp_point_history[index][0] -
                                        base_x) / image_width
        temp_point_history[index][1] = (temp_point_history[index][1] -
                                        base_y) / image_height

    # Convert to a one-dimensional list
    temp_point_history = list(
        itertools.chain.from_iterable(temp_point_history))

    return temp_point_history


def draw_landmarks(image, landmark_point):
    if len(landmark_point) > 0:
        # Thumb
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[3]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[3]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[3]), tuple(landmark_point[4]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[3]), tuple(landmark_point[4]),
                (255, 255, 255), 2)

        # Index finger
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[6]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[6]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[6]), tuple(landmark_point[7]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[6]), tuple(landmark_point[7]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[7]), tuple(landmark_point[8]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[7]), tuple(landmark_point[8]),
                (255, 255, 255), 2)

        # Middle finger
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[10]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[10]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[10]), tuple(landmark_point[11]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[10]), tuple(landmark_point[11]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[11]), tuple(landmark_point[12]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[11]), tuple(landmark_point[12]),
                (255, 255, 255), 2)

        # Ring finger
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[14]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[14]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[14]), tuple(landmark_point[15]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[14]), tuple(landmark_point[15]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[15]), tuple(landmark_point[16]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[15]), tuple(landmark_point[16]),
                (255, 255, 255), 2)

        # Little finger
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[18]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[18]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[18]), tuple(landmark_point[19]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[18]), tuple(landmark_point[19]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[19]), tuple(landmark_point[20]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[19]), tuple(landmark_point[20]),
                (255, 255, 255), 2)

        # Palm
        cv.line(image, tuple(landmark_point[0]), tuple(landmark_point[1]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[0]), tuple(landmark_point[1]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[1]), tuple(landmark_point[2]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[1]), tuple(landmark_point[2]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[5]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[2]), tuple(landmark_point[5]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[9]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[5]), tuple(landmark_point[9]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[13]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[9]), tuple(landmark_point[13]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[17]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[13]), tuple(landmark_point[17]),
                (255, 255, 255), 2)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[0]),
                (0, 0, 0), 6)
        cv.line(image, tuple(landmark_point[17]), tuple(landmark_point[0]),
                (255, 255, 255), 2)

    # Key Points
    for index, landmark in enumerate(landmark_point):
        cv.circle(image, (landmark[0], landmark[1]), 
                  8 if index in [4, 8, 12, 16, 20] else 5,  # Larger circles for fingertips
                  (255, 255, 255), -1)
        cv.circle(image, (landmark[0], landmark[1]), 
                  8 if index in [4, 8, 12, 16, 20] else 5, 
                  (0, 0, 0), 1)

    return image


def draw_bounding_rect(use_brect, image, brect):
    if use_brect:
        # Outer rectangle
        cv.rectangle(image, (brect[0], brect[1]), (brect[2], brect[3]),
                     (0, 0, 0), 1)

    return image


def draw_info_text(image, brect, handedness, hand_sign_text,
                   finger_gesture_text):
    cv.rectangle(image, (brect[0], brect[1]), (brect[2], brect[1] - 22),
                 (0, 0, 0), -1)

    info_text = handedness.classification[0].label[0:]
    if hand_sign_text != "":
        info_text = info_text + ':' + hand_sign_text
    cv.putText(image, info_text, (brect[0] + 5, brect[1] - 4),
               cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv.LINE_AA)

    if finger_gesture_text != "":
        cv.putText(image, "Finger Gesture:" + finger_gesture_text, (10, 60),
                   cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4, cv.LINE_AA)
        cv.putText(image, "Finger Gesture:" + finger_gesture_text, (10, 60),
                   cv.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2,
                   cv.LINE_AA)

    return image


def draw_point_history(image, point_history):
    for index, point in enumerate(point_history):
        if point[0] != 0 and point[1] != 0:
            cv.circle(image, (point[0], point[1]), 1 + int(index / 2),
                      (152, 251, 152), 2)

    return image


if __name__ == '__main__':
    main()