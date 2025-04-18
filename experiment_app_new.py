from __future__ import annotations
import json, random, sys, time, uuid, platform
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

# ────────────────────────────── paths & constants
BASE      = Path(__file__).parent
STIMULI   = BASE / "stimuli.json"
IMG_DIR   = BASE / "images"
LOG_DIR   = BASE / "logs"; LOG_DIR.mkdir(exist_ok=True)
CSV_FILE  = LOG_DIR / "responses.csv"

N_TRUE, N_FALSE, N_PHOTO_EACH = 8, 8, 4

# optional secrets
GSHEET_KEY = st.secrets.get("GSPREAD_KEY")  # entire service‑account JSON as TOML table
GA_ID      = st.secrets.get("GA_ID", {}).get("value")  # GA_ID.value in secrets.toml

# ╭────────────────────────── Google Sheets helper ──────────────────────────╮
if GSHEET_KEY:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    _SCOPE = ["https://spreadsheets.google.com/feeds",
              "https://www.googleapis.com/auth/drive"]
    _CREDS = ServiceAccountCredentials.from_json_keyfile_dict(GSHEET_KEY, _SCOPE)
    _SHEET = gspread.authorize(_CREDS)\
                    .open("Trivia_Responses")\
                    .worksheet("Responses")

    def save_to_gsheet(df: pd.DataFrame) -> None:
        _SHEET.append_rows(df.astype(str).values.tolist())
else:
    def save_to_gsheet(_: pd.DataFrame) -> None: ...

# ╭────────────────────────── stimulus dataclass ───────────────────────────╮
@dataclass
class Stimulus:
    id: str; text: str; truth: bool; photo: str | None; show_photo: bool = False
    @property
    def has_photo(self): return self.photo and self.photo.endswith(".png")
    @property
    def image_path(self): return IMG_DIR/self.photo if self.has_photo else None

def load_stimuli() -> List[Stimulus]:
    return [Stimulus(**d) for d in json.load(STIMULI.open())]

def create_subset(pool: List[Stimulus]) -> List[Stimulus]:
    true  = random.sample([s for s in pool if s.truth],  N_TRUE)
    false = random.sample([s for s in pool if not s.truth], N_FALSE)
    combo = true + false; random.shuffle(combo)

    with_photo = [s for s in combo if s.has_photo]; random.shuffle(with_photo)
    t=f=0
    for s in with_photo:
        if s.truth and t < N_PHOTO_EACH: s.show_photo=True; t+=1
        elif not s.truth and f < N_PHOTO_EACH: s.show_photo=True; f+=1
        if t==N_PHOTO_EACH and f==N_PHOTO_EACH: break
    return combo

# ╭────────────────────────── Google Analytics (optional) ───────────────────╮
if GA_ID:
    st.markdown(
        f"""
        <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){{dataLayer.push(arguments);}}
          gtag('js', new Date());
          gtag('config', '{GA_ID}');
        </script>
        """,
        unsafe_allow_html=True,
    )

# ╭────────────────────────── Streamlit init ────────────────────────────────╮
st.set_page_config("Truth Perception Study", "🤔", "centered")

# new query‑param API only
if "variant" not in st.query_params:
    st.query_params["variant"] = random.choice(["A", "B"])
VARIANT = st.query_params["variant"]
BTN_KW  = {"use_container_width": VARIANT == "B", "type": "primary"}

# session defaults
ss = st.session_state
ss.setdefault("pid",         str(uuid.uuid4()))
ss.setdefault("group",       random.choice(["Explain","Emotion"]))
ss.setdefault("stimuli",     create_subset(load_stimuli()))
ss.setdefault("responses",   [])
ss.setdefault("idx",         0)
ss.setdefault("t_start",     None)

# ╭────────────────────────── UI helpers ────────────────────────────────────╮
def show_instructions():
    st.markdown("### Instructions")
    st.info("Judge each statement **True/False**, then "
            + ("explain your reasoning." if ss.group=="Explain" else "describe your feelings."))
    if st.button("Start", **BTN_KW):
        ss.show_instructions = False
        st.rerun()

def run_trial(stim: Stimulus, i: int, total: int):
    st.subheader(f"Statement {i}/{total}")
    st.write(stim.text)
    if stim.show_photo and stim.image_path.exists():
        st.image(stim.image_path.read_bytes(), width=320)

    if ss.t_start is None: ss.t_start = time.time()
    with st.form(f"f_{stim.id}"):
        ans = st.radio("Is the statement…", ["True","False"], horizontal=True)
        txt = st.text_area("Explain:" if ss.group=="Explain" else "Feelings:", height=120)
        if st.form_submit_button("Submit & Next", **BTN_KW):
            if not txt.strip():
                st.warning("Text box cannot be empty."); st.stop()
            rt = round(time.time() - ss.t_start, 2); ss.t_start=None
            ss.responses.append(dict(
                timestamp=datetime.utcnow().isoformat(),
                participant_id=ss.pid, variant=VARIANT, prompt_group=ss.group,
                stimulus_id=stim.id, truth=stim.truth, answer=ans=="True",
                correct=(ans=="True")==stim.truth, response_text=txt.strip(),
                show_photo=stim.show_photo, rt=rt,
                python=sys.version.split()[0], platform=platform.platform(),
                streamlit=st.__version__,
            ))
            ss.idx += 1; st.rerun()

def finish():
    st.balloons(); st.success("✔️ Responses saved — thank you!")
    df = pd.DataFrame(ss.responses)
    if CSV_FILE.exists():
        df = pd.concat([pd.read_csv(CSV_FILE), df], ignore_index=True)
    df.to_csv(CSV_FILE, index=False); save_to_gsheet(df)

    st.markdown("### Quick stats (session)")
    st.dataframe(df[["stimulus_id","correct","rt"]])

    st.markdown("### Debriefing")
    st.markdown("""
    Thank you for completing this short trivia survey!

    This study investigates how visual cues (unrelated photos) and reasoning style
    (**explanation** vs. **emotion**) influence people’s perception of truth.

    Your responses are recorded **anonymously** and will support research in
    cognitive psychology and digital‑media literacy.

    Questions? Email **aw3088@columbia.edu**.
    """)

# ╭────────────────────────── Main flow ─────────────────────────────────────╮
st.title("🧠 Truth Perception Study" if VARIANT=="A" else "✨ Trivia & Feelings Survey")
if ss.get("show_instructions", True): show_instructions()
elif ss.idx < len(ss.stimuli):           run_trial(ss.stimuli[ss.idx], ss.idx+1, len(ss.stimuli))
else:                                    finish()
