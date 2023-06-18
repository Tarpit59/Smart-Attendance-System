import face_recognition
import os
import csv
import datetime
import numpy as np
import cv2
import PySimpleGUI as sg
import pymysql


# Path to the directory containing the images of users
IMAGES_PATH = r"./Training_images"

# Load the images and encodings of all the users
known_faces = []
known_names = []
attendance_data = []
for image_name in os.listdir(IMAGES_PATH):
    image_path = os.path.join(IMAGES_PATH, image_name)
    image = face_recognition.load_image_file(image_path)
    encoding = face_recognition.face_encodings(image)[0]
    known_faces.append(encoding)
    known_names.append(os.path.splitext(image_name)[0])


def database_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='root',
        db='smart_attendence_system',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection


def insert_into_student_info(name, entry_time):
    connection = database_connection()
    cursor = connection.cursor()
    cursor.execute(
        f'''INSERT INTO student_info(name, entry_time) 
        VALUES ('{name}','{entry_time}');'''
    )
    connection.commit()
    cursor.close()
    connection.close()


# Initialize variables for face recognition
face_locations = []
face_encodings = []
face_names = []

# Initialize variables for attendance tracking
present_names = []
present_times = []

# Define the layout of the UI
layout = [
    [sg.Text("Smart Attendance System", font=("Arial", 16))],
    [sg.Image(filename="", key="-IMAGE-"), sg.Column([[sg.Text("",
                                                               size=(20, 1), key=f"-NAME-{i}")] for i in range(len(known_names))])],
    [sg.Button("Start", key="-START-", size=(10, 1)), sg.Button("Stop",
                                                                key="-STOP-", size=(10, 1)), sg.Button("Exit", key="-EXIT-", size=(10, 1))]
]

# Create the UI window
window = sg.Window("Smart Attendance System", layout)

# Initialize variables for video capture
cap = None
video_on = False

while True:
    # Read the events from the UI window
    event, values = window.read(timeout=2)

    # Start the video stream if the 'Start' button is pressed
    if event == "-START-" and not video_on:
        cap = cv2.VideoCapture(0)
        # cap = cv2.VideoCapture('./vid.mp4')
        # cap = cv2.VideoCapture("http://192.168.1.3:4747/video")
        video_on = True

    # Stop the video stream if the 'Stop' button is pressed
    elif event == "-STOP-" and video_on:
        cap.release()
        video_on = False

    # Exit the program if the 'Exit' button is pressed or the window is closed
    elif event == "-EXIT-" or event == sg.WIN_CLOSED:
        break

    # Capture a frame from the video stream
    if video_on:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize the frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the color space of the frame from BGR to RGB
        rgb_frame = small_frame[:, :, ::-1]

        # Find the face locations and encodings in the frame
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(
            rgb_frame, face_locations)

        # Identify the names of the faces in the frame
        face_names = []

        for face_encoding in face_encodings:
            # See if the face is a match for any known face(s)
            matches = face_recognition.compare_faces(
                known_faces, face_encoding)
            # If a match was found in the known face(s) list, use the first one
            if True in matches:
                first_match_index = matches.index(True)
                name = known_names[first_match_index]

                # Check if the same user face was recognized within 30 seconds
                current_time = datetime.datetime.now()
                for data in attendance_data:
                    if name == data[0] and (current_time - data[1]).seconds < 30:
                        break
                else:
                    # Store attendance data
                    attendance_data.append((name, current_time))
                    insert_into_student_info(name, current_time)

                # Add the name to the list of recognized names
                face_names.append(name)

        # Display the face recognition results in the UI window
        for i, name in enumerate(face_names):
            window[f"-NAME-{i}"].update(name)

        # Resize the frame for displaying in the UI window
        frame = cv2.resize(frame, (640, 480))

        # Draw the face recognition results on the frame
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.rectangle(frame, (left, bottom - 35),
                          (right, bottom), (0, 255, 0), cv2.FILLED)
            cv2.putText(frame, name, (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1)

        # Display the frame in the UI window
        imgbytes = cv2.imencode(".png", frame)[1].tobytes()
        window["-IMAGE-"].update(data=imgbytes)

# Release the video stream and destroy the UI window
if cap is not None:
    cap.release()
    window.close()