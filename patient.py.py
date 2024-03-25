import streamlit as st
import sqlite3
import cv2
import os
import tempfile
import requests
from bs4 import BeautifulSoup
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import random

# Create a connection to the database
conn = sqlite3.connect('healthcare.db')
c = conn.cursor()

# Create the users table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             username TEXT UNIQUE NOT NULL,
             password TEXT NOT NULL,
             name TEXT NOT NULL,
             age INTEGER NOT NULL,
             gender TEXT NOT NULL,
             profile_picture TEXT,
             address TEXT NOT NULL,
             user_type TEXT NOT NULL)''')

# Create the consultations table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS consultations
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             patient_id INTEGER NOT NULL,
             consultation_type TEXT NOT NULL,
             symptoms TEXT,
             history_of_illness TEXT,
             blood_group TEXT,
             comments TEXT,
             status TEXT NOT NULL,
             doctor_comments TEXT,
             FOREIGN KEY (patient_id) REFERENCES users (id))''')

# Create the chat_messages table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS chat_messages
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             consultation_id INTEGER NOT NULL,
             sender TEXT NOT NULL,
             message TEXT NOT NULL,
             timestamp TEXT NOT NULL,
             FOREIGN KEY (consultation_id) REFERENCES consultations (id))''')

conn.commit()

# Patient Signup
def patient_signup():
    st.subheader("Patient Signup")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    name = st.text_input("Name")
    age = st.number_input("Age", min_value=0, max_value=150, step=1)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    profile_picture = st.file_uploader("Profile Picture", type=["jpg", "jpeg", "png"])
    address = st.text_area("Address")

    if st.button("Sign Up"):
        # Check if the username already exists
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = c.fetchone()

        if existing_user:
            st.error("Username already exists. Please choose a different username.")
        else:
            # Save the profile picture to a file
            if profile_picture:
                profile_picture_path = f"profile_{username}.jpg"
                with open(profile_picture_path, "wb") as file:
                    file.write(profile_picture.getbuffer())
            else:
                profile_picture_path = None

            # Insert the patient data into the users table
            c.execute("INSERT INTO users (username, password, name, age, gender, profile_picture, address, user_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (username, password, name, age, gender, profile_picture_path, address, "patient"))
            conn.commit()
            st.success("Patient account created successfully!")

# Patient Login
def patient_login():
    st.subheader("Patient Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Check if the username and password match a patient user
        c.execute("SELECT * FROM users WHERE username = ? AND password = ? AND user_type = ?",
                  (username, password, "patient"))
        patient_user = c.fetchone()

        if patient_user:
            st.success("Logged in as a patient!")
            st.session_state.logged_in = True
            st.session_state.user = patient_user
            st.experimental_rerun()
        else:
            st.error("Invalid username or password.")

# Knowledge Base
def generate_dataset():
    # Generate a diverse dataset of medical question-answer pairs
    data = pd.DataFrame({
        "question": [
            "What are the symptoms of COVID-19?",
            "How does COVID-19 spread?",
            "What are the treatment options for COVID-19?",
            "What are the symptoms of diabetes?",
            "What causes diabetes?",
            "What are the complications of diabetes?",
            "What are the symptoms of heart disease?",
            "What are the risk factors for heart disease?",
            "What are the treatment options for heart disease?",
            "What are the symptoms of asthma?",
            "What triggers asthma attacks?",
            "How is asthma treated?",
            "What are the symptoms of depression?",
            "What causes depression?",
            "What are the treatment options for depression?",
            "What are the symptoms of high blood pressure?",
            "What causes high blood pressure?",
            "How is high blood pressure treated?",
            "What are the symptoms of a migraine?",
            "What triggers migraines?",
            "What are the treatment options for migraines?",
            "What are the symptoms of an allergic reaction?",
            "What causes allergic reactions?",
            "How are allergic reactions treated?",
            "What are the symptoms of a urinary tract infection (UTI)?",
            "What causes urinary tract infections?",
            "How are urinary tract infections treated?"
        ],
        "answer": [
            "Common symptoms of COVID-19 include fever, cough, tiredness, and loss of taste or smell.",
            "COVID-19 spreads primarily through respiratory droplets when an infected person coughs, sneezes, or talks.",
            "Treatment for COVID-19 typically involves supportive care to help relieve symptoms and manage complications.",
            "Common symptoms of diabetes include increased thirst, frequent urination, extreme hunger, and unexplained weight loss.",
            "Diabetes is caused by a combination of genetic and environmental factors.",
            "Complications of diabetes can include heart disease, kidney damage, nerve damage, and eye problems.",
            "Common symptoms of heart disease include chest pain or discomfort, shortness of breath, and fatigue.",
            "Risk factors for heart disease include high blood pressure, high cholesterol, smoking, and obesity.",
            "Treatment options for heart disease may include lifestyle changes, medications, angioplasty, or surgery.",
            "Symptoms of asthma include wheezing, chest tightness, shortness of breath, and coughing.",
            "Asthma attacks can be triggered by allergens, respiratory infections, exercise, cold air, and stress.",
            "Asthma is treated with a combination of long-term control medications and quick-relief medications.",
            "Symptoms of depression include persistent sadness, loss of interest, changes in sleep and appetite, and feelings of hopelessness.",
            "Depression can be caused by a combination of genetic, biological, environmental, and psychological factors.",
            "Treatment options for depression may include therapy, medication, or a combination of both.",
            "Symptoms of high blood pressure often include no symptoms at all, which is why it is known as the 'silent killer'.",
            "High blood pressure can be caused by factors such as age, family history, obesity, and lifestyle habits.",
            "High blood pressure is treated with lifestyle changes, such as a healthy diet and regular exercise, and medications.",
            "Symptoms of a migraine include severe headache, sensitivity to light and sound, nausea, and vomiting.",
            "Migraines can be triggered by hormonal changes, stress, certain foods and drinks, and changes in sleep patterns.",
            "Treatment options for migraines may include pain-relieving medications, preventive medications, and lifestyle changes.",
            "Symptoms of an allergic reaction can include itching, rash, hives, swelling, difficulty breathing, and anaphylaxis.",
            "Allergic reactions are caused by an overreaction of the immune system to a typically harmless substance.",
            "Allergic reactions are treated with antihistamines, corticosteroids, and epinephrine in severe cases.",
            "Symptoms of a urinary tract infection include a frequent urge to urinate, burning sensation during urination, and cloudy or bloody urine.",
            "Urinary tract infections are caused by bacteria entering the urinary tract, usually through the urethra.",
            "Urinary tract infections are treated with antibiotics to eliminate the bacterial infection."
        ]
    })
    return data

def search_answers(query, data):
    # Vectorize the questions and the query
    vectorizer = TfidfVectorizer()
    question_vectors = vectorizer.fit_transform(data["question"])
    query_vector = vectorizer.transform([query])

    # Calculate cosine similarity between the query and questions
    similarity_scores = cosine_similarity(query_vector, question_vectors)

    # Get the top 3 most similar questions and their corresponding answers
    top_indices = similarity_scores.argsort()[0][-3:][::-1]
    top_results = data.iloc[top_indices][["question", "answer"]]

    return top_results

def knowledge_base_component():
    st.subheader("Knowledge Base")
    query = st.text_input("Enter your medical question")

    if st.button("Search"):
        try:
            # Generate the dataset
            data = generate_dataset()

            # Search for relevant answers
            results = search_answers(query, data)

            # Display the search results
            if len(results) > 0:
                for _, row in results.iterrows():
                    st.subheader(row["question"])
                    st.write(row["answer"])
                    st.write("---")
            else:
                st.warning("No relevant answers found. Please consider setting up a meeting with a doctor for further assistance.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Patient Dashboard
def patient_dashboard():
    st.subheader(f"Welcome, {st.session_state.user[3]}!")

    # Display menu options
    menu = ["Chat Consultations", "Video Consultations", "Knowledge Base"]
    choice = st.sidebar.selectbox("Select an option", menu)

    if choice == "Chat Consultations":
        st.subheader("Chat Consultations")

        # Create a new chat consultation
        st.subheader("New Chat Consultation")
        symptoms = st.text_area("Symptoms")
        history_of_illness = st.text_area("History of Illness")
        blood_group = st.text_input("Blood Group")
        comments = st.text_area("Comments")

        if st.button("Submit"):
            # Insert the consultation data into the consultations table
            c.execute("INSERT INTO consultations (patient_id, consultation_type, symptoms, history_of_illness, blood_group, comments, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (st.session_state.user[0], "chat", symptoms, history_of_illness, blood_group, comments, "Processing"))
            conn.commit()
            st.success("Chat consultation submitted successfully!")

        # Display chat consultations for the patient
        st.subheader("Chat Consultations")
        c.execute("SELECT * FROM consultations WHERE patient_id = ? AND consultation_type = 'chat'",
                  (st.session_state.user[0],))
        chat_consultations = c.fetchall()

        for consultation in chat_consultations:
            st.write(f"Consultation ID: {consultation[0]}")
            st.write(f"Symptoms: {consultation[3]}")
            st.write(f"History of Illness: {consultation[4]}")
            st.write(f"Blood Group: {consultation[5]}")
            st.write(f"Comments: {consultation[6]}")
            st.write(f"Status: {consultation[7]}")
            st.write(f"Doctor Comments: {consultation[8]}")

            if consultation[7] == "Available":
                # Real-time chat functionality
                chat_section = st.empty()
                message_input = st.text_input("Enter your message", key=f"message_{consultation[0]}")
                send_button = st.button("Send", key=f"send_{consultation[0]}")

                # Fetch chat messages for the consultation
                c.execute("SELECT * FROM chat_messages WHERE consultation_id = ?", (consultation[0],))
                chat_messages = c.fetchall()

                # Display chat messages
                with chat_section.container():
                    for message in chat_messages:
                        st.write(f"{message[2]}: {message[3]} ({message[4]})")

                # Send chat message
                if send_button:
                    if message_input:
                        c.execute("INSERT INTO chat_messages (consultation_id, sender, message, timestamp) VALUES (?, ?, ?, datetime('now'))",
                                  (consultation[0], "Patient", message_input))
                        conn.commit()
                        st.experimental_rerun()

            st.write("---")

    elif choice == "Video Consultations":
        st.subheader("Video Consultations")

        # Create a new video consultation
        st.subheader("New Video Consultation")
        symptoms = st.text_area("Symptoms")
        history_of_illness = st.text_area("History of Illness")
        blood_group = st.text_input("Blood Group")
        comments = st.text_area("Comments")

        if st.button("Submit"):
            # Insert the consultation data into the consultations table
            c.execute("INSERT INTO consultations (patient_id, consultation_type, symptoms, history_of_illness, blood_group, comments, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (st.session_state.user[0], "video", symptoms, history_of_illness, blood_group, comments, "Processing"))
            conn.commit()
            st.success("Video consultation submitted successfully!")

        # Display video consultations for the patient
        st.subheader("Video Consultations")
        c.execute("SELECT * FROM consultations WHERE patient_id = ? AND consultation_type = 'video'",
                  (st.session_state.user[0],))
        video_consultations = c.fetchall()

        for consultation in video_consultations:
            st.write(f"Consultation ID: {consultation[0]}")
            st.write(f"Symptoms: {consultation[3]}")
            st.write(f"History of Illness: {consultation[4]}")
            st.write(f"Blood Group: {consultation[5]}")
            st.write(f"Comments: {consultation[6]}")
            st.write(f"Status: {consultation[7]}")
            st.write(f"Doctor Comments: {consultation[8]}")

            if consultation[7] == "Available":
                # Record and save patient's video
                if st.button("Record Video", key=f"record_{consultation[0]}"):
                    # Open the default camera
                    cap = cv2.VideoCapture(0)

                    # Define the codec and create VideoWriter object
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    patient_video_path = f"consultation_{consultation[0]}_patient.mp4"
                    out = cv2.VideoWriter(patient_video_path, fourcc, 20.0, (640, 480))

                    # Record the video for 1 minute
                    start_time = cv2.getTickCount()
                    while (cv2.getTickCount() - start_time) / cv2.getTickFrequency() < 60:
                        ret, frame = cap.read()
                        if ret:
                            out.write(frame)
                        else:
                            break

                    # Release the camera and close the output file
                    cap.release()
                    out.release()
                    st.success("Video recorded successfully!")

                # Check if a doctor's video exists for the consultation
                doctor_video_path = f"consultation_{consultation[0]}_doctor.mp4"
                if os.path.exists(doctor_video_path):
                    # Display the doctor's video
                    video_file = open(doctor_video_path, 'rb')
                    video_bytes = video_file.read()
                    st.video(video_bytes)

            st.write("---")

    elif choice == "Knowledge Base":
        knowledge_base_component()

# Main App
def main():
    st.title("Healthcare Application - Patient")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        menu = ["Login", "Signup"]
        choice = st.sidebar.selectbox("Select an option", menu)

        if choice == "Login":
            patient_login()
        elif choice == "Signup":
            patient_signup()
    else:
        patient_dashboard()

        # Logout button
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.experimental_rerun()

if __name__ == '__main__':
    main()