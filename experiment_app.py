
import streamlit as st
import time
import pandas as pd
import random
import uuid
import json
import os

with open("stimuli.json", "r") as f:
    full_stimuli = json.load(f)

true_pool = [s for s in full_stimuli if s["truth"]]
false_pool = [s for s in full_stimuli if not s["truth"]]

def create_balanced_stimuli(n_true=8, n_false=8, n_photo_each=4):
    sampled_true = random.sample(true_pool, n_true)
    sampled_false = random.sample(false_pool, n_false)

    def assign_photos(sampled, n_photo):
        with_photo = [s for s in sampled if s["photo"]]
        selected_ids = set(s["id"] for s in random.sample(with_photo, min(n_photo, len(with_photo))))
        for s in sampled:
            s["show_photo"] = s["id"] in selected_ids
        return sampled

    balanced_true = assign_photos(sampled_true, n_photo_each)
    balanced_false = assign_photos(sampled_false, n_photo_each)

    final_list = balanced_true + balanced_false
    random.shuffle(final_list)
    return final_list

#for storing infomation purpose
#participant idf, group they are assigned to, which subset of stimuli they got and their responses
if "participant_id" not in st.session_state:
    st.session_state.participant_id = str(uuid.uuid4())

if "group" not in st.session_state:
    st.session_state.group = random.choice(["Explain", "Emotion"])

if "stimuli_subset" not in st.session_state:
    st.session_state.stimuli_subset = create_balanced_stimuli()

if "responses" not in st.session_state:
    st.session_state.responses = []

if "current_index" not in st.session_state:
    st.session_state.current_index = 0

# UI
st.title("Trivia!")
# Instruction screen (before first question)
if st.session_state.current_index == 0 and not st.session_state.get("instructions_shown", False):
    st.markdown("### Instructions")
    st.markdown("""
    Welcome! This is a trivia quiz. You will be presented with a series of factual statements — some of them are true, some are false.

    Your task is to decide whether each statement is **True** or **False**. 

    Additionally:
    """)
    if st.session_state.group == "Explain":
        st.markdown("- Provide a **brief explanation** of why you think the statement is true or false.")
    else:
        st.markdown("- Share **how the statement makes you feel** — your emotional response.")

    st.markdown("""
    Please answer as accurately and thoughtfully as you can. The quiz will begin once you click the button below.
    """)
    if st.button("Start Quiz"):
        st.session_state.instructions_shown = True
        st.rerun()
    st.stop()

stimuli = st.session_state.stimuli_subset
current_idx = st.session_state.current_index

if current_idx < len(stimuli):
    stim = stimuli[current_idx]
    st.subheader(f"Statement {current_idx + 1} of {len(stimuli)}")
    st.write(stim["text"])

    # Build image path if a photo is assigned
    image_path = os.path.join("images", stim["photo"]) if stim["photo"] else None

    # Check if image file exists before trying to display it
    if stim["show_photo"] and image_path and os.path.exists(image_path):
        st.image(image_path, width=300)

    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()
        
    answer = st.radio("Is this statement true or false?", ["True", "False"])

    if st.session_state.group == "Explain":
        response_text = st.text_area("Explain your answer:")
    else:
        response_text = st.text_area("How does this statement make you feel:")

    if st.button("Submit and Continue"): # only if they finished the experiment and data will be saved
        rt = round(time.time() - st.session_state.start_time, 2)
        st.session_state.responses.append({
            "participant_id": st.session_state.participant_id,
            "group": st.session_state.group,
            "stimulus_id": stim["id"],
            "text": stim["text"],
            "truth": stim["truth"],
            "photo": stim["photo"],
            "show_photo": stim["show_photo"],
            "answer": answer,
            "response_text": response_text,
            "response_time": rt
        })
        st.session_state.current_index += 1
        st.rerun()
else:
    st.balloons()
    st.success("Thank you for participating! Your responses have been saved.")

    # Save to master file
    df = pd.DataFrame(st.session_state.responses)
    master_file = "all_responses.csv"

    if os.path.exists(master_file):
        existing = pd.read_csv(master_file)
        df = pd.concat([existing, df], ignore_index=True)

    df.to_csv(master_file, index=False)

    # DEBRIEFING
    # this is needed since experiment has the element of deceiving people
    st.markdown("### 📘 Debriefing")
    st.markdown("""
    Thank you for completing this short trivia survey!

    This study is part of a research project investigating how visual cues (like unrelated photos) and different kinds of reasoning (explanation vs. emotion) affect people’s perception of truth.

    Some of the statements you saw were factually accurate, while others were not. And some were accompanied by images that were not directly related to the content.

    By analyzing how people respond under different conditions, we hope to better understand how misinformation spreads online — especially when it's paired with persuasive visuals.

    Your responses have been recorded anonymously and will help support research in cognitive psychology and digital media literacy.

    If you have any questions, feel free to reach out to the research team at **aw3088@columbia.edu**. Thank you again!
    """)
