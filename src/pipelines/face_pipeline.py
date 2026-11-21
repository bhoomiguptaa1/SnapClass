

import os
import sys
import shutil
import tempfile
from pathlib import Path
import dlib
import numpy as np
import face_recognition_models
from sklearn.svm import SVC
import streamlit as st

from src.database.db import get_all_students


def _get_safe_model_path(model_path: str) -> str:
    """
    dlib uses C++ std::ifstream on Windows, which fails when paths contain
    non-ASCII / Unicode characters (such as Chinese characters '文件' in OneDrive paths).
    This function returns an ASCII-safe path from TEMP, converts to 8.3 short path, or copies to TEMP.
    """
    if not model_path:
        return model_path

    # First check pre-cached ASCII temp directory
    temp_file = Path(tempfile.gettempdir()) / "snapclass_models" / Path(model_path).name
    if temp_file.exists():
        return str(temp_file)

    # Check if the path is already pure ASCII and exists
    try:
        model_path.encode('ascii')
        is_ascii = True
    except UnicodeEncodeError:
        is_ascii = False

    if is_ascii and os.path.exists(model_path):
        return model_path

    # Method 1: Convert to Windows 8.3 short path (ASCII-only aliases for folders like '文件')
    if sys.platform == 'win32':
        try:
            import ctypes
            buffer = ctypes.create_unicode_buffer(500)
            res = ctypes.windll.kernel32.GetShortPathNameW(str(model_path), buffer, len(buffer))
            if res > 0:
                short_path = buffer.value
                try:
                    short_path.encode('ascii')
                    if os.path.exists(short_path):
                        return short_path
                except UnicodeEncodeError:
                    pass
        except Exception:
            pass

    # Method 2: Copy to an ASCII-safe temporary folder
    try:
        temp_dir = Path(tempfile.gettempdir()) / "snapclass_models"
        temp_dir.mkdir(parents=True, exist_ok=True)
        safe_file = temp_dir / Path(model_path).name
        if not safe_file.exists() or safe_file.stat().st_size != os.path.getsize(model_path):
            shutil.copy2(model_path, safe_file)
        return str(safe_file)
    except Exception:
        return model_path


@st.cache_resource
def load_dlib_models():
    detector = dlib.get_frontal_face_detector() 

    pose_model_path = _get_safe_model_path(
        face_recognition_models.pose_predictor_model_location()
    )
    sp = dlib.shape_predictor(pose_model_path)

    face_rec_model_path = _get_safe_model_path(
        face_recognition_models.face_recognition_model_location()
    )
    facerec = dlib.face_recognition_model_v1(face_rec_model_path)

    return detector, sp, facerec

def get_face_embeddings(image_np):
    # Ensure image is 3-channel RGB uint8
    if image_np.ndim == 2:
        image_np = np.stack([image_np] * 3, axis=-1)
    elif image_np.ndim == 3 and image_np.shape[2] == 4:
        image_np = image_np[:, :, :3]
    if image_np.dtype != np.uint8:
        image_np = image_np.astype(np.uint8)

    detector, sp, facerec = load_dlib_models()
    faces = detector(image_np, 1)

    encodings = []
    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 1)
        encodings.append(np.array(face_descriptor))
    return encodings

@st.cache_resource(ttl=60)
def get_trained_model():
    X = []
    y = []

    student_db = get_all_students()

    if not student_db:
        return None
    
    for student in student_db:
        embedding = student.get('face_embedding')
        if embedding:
            X.append(np.array(embedding))
            y.append(student.get('student_id'))

    if len(X) == 0:
        return None
    
    clf = SVC(kernel='linear', probability=True, class_weight='balanced')
    try:
        clf.fit(X, y)
    except Exception:
        pass

    return {'clf': clf, 'X': X, 'y': y}

def train_classifier():
    st.cache_resource.clear()
    model_data = get_trained_model()
    return bool(model_data)

def predict_attendance(class_image_np):
    encodings = get_face_embeddings(class_image_np)
    detected_student = {}

    model_data = get_trained_model()
    if not model_data or not model_data.get('X'):
        return detected_student, [], len(encodings)
    
    X_train = model_data['X']
    y_train = model_data['y']
    all_students = sorted(list(set(y_train)))

    resemblance_threshold = 0.48

    for encoding in encodings:
        best_sid = None
        min_dist = float('inf')

        # Compare against all enrolled embeddings to find true closest match
        for s_emb, s_id in zip(X_train, y_train):
            dist = np.linalg.norm(np.array(s_emb) - encoding)
            if dist < min_dist:
                min_dist = dist
                best_sid = int(s_id)

        if best_sid is not None and min_dist <= resemblance_threshold:
            detected_student[best_sid] = True

    return detected_student, all_students, len(encodings)

