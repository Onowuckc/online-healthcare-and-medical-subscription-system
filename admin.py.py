import streamlit as st
import sqlite3
import cv2
import os
import tempfile

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

# Admin Signup
def admin_signup():
    st.subheader("Admin Signup")
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

            # Insert the admin data into the users table
            c.execute("INSERT INTO users (username, password, name, age, gender, profile_picture, address, user_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (username, password, name, age, gender, profile_picture_path, address, "admin"))
            conn.commit()
            st.success("Admin account created successfully!")

# Admin Login
def admin_login():
    st.subheader("Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Check if the username and password match an admin user
        c.execute("SELECT * FROM users WHERE username = ? AND password = ? AND user_type = ?",
                  (username, password, "admin"))
        admin_user = c.fetchone()

        if admin_user:
            st.success("Logged in as an admin!")
            st.session_state.logged_in = True
            st.session_state.user = admin_user
            st.experimental_rerun()
        else:
            st.error("Invalid username or password.")

# Admin Dashboard
def admin_dashboard():
    st.subheader(f"Welcome, {st.session_state.user[3]}!")

    # Fetch all registered patients
    c.execute("SELECT * FROM users WHERE user_type = 'patient'")
    patients = c.fetchall()

    # Display registered patients
    for patient in patients:
        st.write(f"Patient ID: {patient[0]}")
        st.write(f"Name: {patient[3]}")
        st.write(f"Age: {patient[4]}")
        st.write(f"Gender: {patient[5]}")
        st.write(f"Address: {patient[7]}")
        st.write("---")

# Chat Consultation
def chat_consultation():
    st.subheader("Chat Consultations")

    # Fetch chat consultations
    c.execute("SELECT * FROM consultations WHERE consultation_type = 'chat'")
    consultations = c.fetchall()

    # Display chat consultations
    for consultation in consultations:
        st.write(f"Consultation ID: {consultation[0]}")
        st.write(f"Patient ID: {consultation[1]}")
        st.write(f"Symptoms: {consultation[3]}")
        st.write(f"History of Illness: {consultation[4]}")
        st.write(f"Blood Group: {consultation[5]}")
        st.write(f"Comments: {consultation[6]}")
        st.write(f"Status: {consultation[7]}")
        st.write(f"Doctor Comments: {consultation[8]}")

        # Update consultation status and initiate chat
        new_status = st.selectbox("Update Status", ["Processing", "Available", "Unavailable"], key=f"status_{consultation[0]}")
        doctor_comments = st.text_area("Doctor Comments", key=f"comments_{consultation[0]}")

        if st.button("Update", key=f"update_{consultation[0]}"):
            c.execute("UPDATE consultations SET status = ?, doctor_comments = ? WHERE id = ?",
                      (new_status, doctor_comments, consultation[0]))
            conn.commit()
            st.success("Consultation updated successfully!")

        if new_status == "Available":
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
                              (consultation[0], "Doctor", message_input))
                    conn.commit()
                    st.experimental_rerun()

        st.write("---")

# Video Consultation
def video_consultation():
    st.subheader("Video Consultations")

    # Fetch video consultations
    c.execute("SELECT * FROM consultations WHERE consultation_type = 'video'")
    consultations = c.fetchall()

    # Display video consultations
    for consultation in consultations:
        st.write(f"Consultation ID: {consultation[0]}")
        st.write(f"Patient ID: {consultation[1]}")
        st.write(f"Symptoms: {consultation[3]}")
        st.write(f"History of Illness: {consultation[4]}")
        st.write(f"Blood Group: {consultation[5]}")
        st.write(f"Comments: {consultation[6]}")
        st.write(f"Status: {consultation[7]}")
        st.write(f"Doctor Comments: {consultation[8]}")

        # Update consultation status and view/record video
        new_status = st.selectbox("Update Status", ["Processing", "Available", "Unavailable"], key=f"status_{consultation[0]}")
        doctor_comments = st.text_area("Doctor Comments", key=f"comments_{consultation[0]}")

        if st.button("Update", key=f"update_{consultation[0]}"):
            c.execute("UPDATE consultations SET status = ?, doctor_comments = ? WHERE id = ?",
                      (new_status, doctor_comments, consultation[0]))
            conn.commit()
            st.success("Consultation updated successfully!")

        # Check if a video exists for the consultation
        doctor_video_path = f"consultation_{consultation[0]}_doctor.mp4"
        patient_video_path = f"consultation_{consultation[0]}_patient.mp4"

        if os.path.exists(doctor_video_path):
            # Display the doctor's video
            doctor_video_file = open(doctor_video_path, 'rb')
            doctor_video_bytes = doctor_video_file.read()
            st.video(doctor_video_bytes)

        if os.path.exists(patient_video_path):
            # Display the patient's video
            patient_video_file = open(patient_video_path, 'rb')
            patient_video_bytes = patient_video_file.read()
            st.video(patient_video_bytes)

        # Record and save doctor's video
        if st.button("Record Video", key=f"record_{consultation[0]}"):
            # Open the default camera
            cap = cv2.VideoCapture(0)

            # Define the codec and create VideoWriter object
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(doctor_video_path, fourcc, 20.0, (640, 480))

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

        st.write("---")

# Main App
def main():
    st.title("Healthcare Application - Admin")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        menu = ["Login", "Signup"]
        choice = st.sidebar.selectbox("Select an option", menu)

        if choice == "Login":
            admin_login()
        elif choice == "Signup":
            admin_signup()
    else:
        menu = ["Dashboard", "Chat Consultation", "Video Consultation"]
        choice = st.sidebar.selectbox("Select an option", menu)

        if choice == "Dashboard":
            admin_dashboard()
        elif choice == "Chat Consultation":
            chat_consultation()
        elif choice == "Video Consultation":
            video_consultation()

        # Logout button
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.experimental_rerun()

if __name__ == '__main__':
    main()