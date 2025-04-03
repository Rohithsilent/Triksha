🖐️ Triksha: The Jedi of Gesture Recognition

Welcome to Triksha, an AI-powered wizardry for recognizing hand gestures using MediaPipe and TensorFlow. With Triksha, you can wave, point, and even do secret ninja moves to interact with digital interfaces. Whether you’re crafting an accessibility tool, gaming without a controller, or just trying to impress your cat—Triksha has got you covered!


---



🌟 What's Inside?

This repository is your ultimate gesture-powered toolkit, featuring:

A sample program (because we all need a starting point).

A Hand Sign Recognition Model (TFLite) for those crisp finger poses.

A Finger Gesture Recognition Model (TFLite) for tracking those intricate moves.

Datasets and Jupyter notebooks to train Triksha to recognize your weirdest hand signals.



---

🚀 Requirements

Before summoning the power of Triksha, ensure your system has these enchanted packages installed:

mediapipe 0.8.1 (for mystical hand-tracking)

OpenCV 3.4.2 or later (so you can see what you're doing)

TensorFlow 2.3.0 or later (or tf-nightly 2.5.0.dev+ if you like living on the edge)

scikit-learn 0.23.2+ (for those who love confusion matrices)

matplotlib 3.3.2+ (because graphs make us feel smart)



---

💻 Demo Time!

Fire up the demo and let your hands do the talking:

streamlit run app.py


---

🔮 The Magic Behind the Scenes

app.py

This is where the magic happens! Run this to:

Infer gestures with pre-trained models.

Gather new training data for better recognition.


keypoint_classification.ipynb

A Jupyter notebook that teaches Triksha how to interpret hand signs like "peace," "rock on," and "why is my code not working?!"

point_history_classification.ipynb

Another Jupyter notebook, but this one focuses on gesture recognition—like tracking finger movement history for extra precision.

Model Directories

model/keypoint_classifier/

Stores hand sign recognition goodies: training data, models, labels, and inference modules.


model/point_history_classifier/

Houses finger gesture recognition treasures, including trained models and datasets.


utils/cvfpscalc.py

A speedometer for your frames-per-second. Because smooth gestures matter.



---

🎭 Training: Make Triksha Smarter!

Want to teach Triksha your own secret hand gestures? Here’s how:

👋 Hand Sign Recognition Training

Step 1: Collecting Data

Press 'k' to enter keypoint logging mode.

Press 0-9 to save different hand poses to keypoint.csv.

By default, it knows "open hand," "closed hand," and "pointing"—but you can teach it more!


Step 2: Model Training

Open keypoint_classification.ipynb in Jupyter.

Change NUM_CLASSES if you're adding more signs.

Update keypoint_classifier_label.csv with your new labels.

Run all the cells and watch Triksha level up!


🔄 Finger Gesture Recognition Training

Step 1: Data Collection

Press 'h' to start logging finger movement history.

Press 0-9 to save different motion patterns to point_history.csv.

Default motions include "stationary," "clockwise," "counterclockwise," and "moving."


Step 2: Training the Model

Open point_history_classification.ipynb in Jupyter.

Adjust NUM_CLASSES for additional movements.

Modify point_history_classifier_label.csv to reflect new gestures.

Run all the cells, and voila!



---

📓 Reference

MediaPipe (where the real magic happens)


Now go forth and wield the power of gestures like the tech wizard you are! 🖐️

