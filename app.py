import streamlit as st
import pandas as pd
import re
from rapidfuzz import process, fuzz

# --- Streamlit config ---
st.set_page_config(page_title="☀️ Solar Radiation Assistant", layout="wide")
st.title("☀️ Solar Radiation Assistant")

# --- Load Excel ---
EXCEL_FILE = "CombinedData.xlsx"
df = pd.read_excel(EXCEL_FILE)

# --- Normalize ---
df.columns = df.columns.str.strip()
df['Type'] = df['Type'].str.strip().str.lower()
df['State'] = df['State'].fillna("").str.strip().str.title()
df['District'] = df['District'].fillna("").str.strip().str.title()
df['Substation'] = df['Substation'].fillna("").str.strip().str.title()
df['Site'] = df['Site'].fillna("").str.strip().str.title()

# --- Utility functions ---
def fuzzy_match(query, choices, limit=5, score_cutoff=80):
    query = query.strip().lower()
    norm_choices = {c.lower(): c for c in choices if isinstance(c, str) and c.strip() != ""}
    matches = process.extract(query, norm_choices.keys(), scorer=fuzz.WRatio, limit=limit)
    return [norm_choices[m[0]] for m in matches if m[1] >= score_cutoff]

def fuzzy_match_best(query, choices):
    norm_choices = {c.lower(): c for c in choices if isinstance(c, str) and c.strip() != ""}
    match = process.extractOne(query.strip().lower(), norm_choices.keys(), scorer=fuzz.WRatio)
    if match:
        return norm_choices[match[0]], match[1]
    return None, 0

def extract_top_n(query):
    try:
        return int(re.findall(r"top (\\d+)", query.lower())[0])
    except:
        return 5

def show_row(row):
    return row[['State','District','Substation','Site','SolarGIS GHI','Metonorm 8.2 GHI','Albedo']]

# --- Query handler ---
def answer_query(q):
    q_lower = q.strip().lower()
    best_type, best_name, best_score = None, None, 0
    for t in ["substation", "district", "site"]:
        name, score = fuzzy_match_best(q, df[df['Type']==t][t.capitalize()].unique())
        if score > best_score:
            best_type, best_name, best_score = t, name, score

    keywords = ["substation","district","site","state","ghi","radiation","top","average","highest","largest","biggest"]
    if best_score >= 82 and (not any(word in q_lower for word in keywords) or best_score >= 90):
        if best_type == "substation":
            return df[df['Type']=="substation"].loc[df['Substation']==best_name][['State','District','Substation','SolarGIS GHI','Metonorm 8.2 GHI','Albedo']]
        if best_type == "district":
            return df[df['Type']=="district"].loc[df['District']==best_name][['State','District','SolarGIS GHI','Albedo']]
        if best_type == "site":
            return df[df['Type']=="site"].loc[df['Site']==best_name][['State','District','Site','SolarGIS GHI','Metonorm 8.2 GHI','Albedo']]

    # ---------------- SUBSTATION QUERIES ----------------
    if "substation" in q_lower:
        sub_df = df[df['Type']=="substation"]
        n = extract_top_n(q_lower)

        # State filter
        for state in df['State'].dropna().unique():
            if state.lower() in q_lower:
                state_df = sub_df[sub_df['State'].str.lower()==state.lower()]
                if "highest" in q_lower or "top" in q_lower:
                    return state_df.nlargest(n,"SolarGIS GHI")[['State','District','Substation','SolarGIS GHI']].reset_index(drop=True)

        # District filter
        for district in df['District'].dropna().unique():
            if district.lower() in q_lower:
                dist_df = sub_df[sub_df['District'].str.lower()==district.lower()]
                if "highest" in q_lower or "top" in q_lower:
                    return dist_df.nlargest(n,"SolarGIS GHI")[['State','District','Substation','SolarGIS GHI']].reset_index(drop=True)

        if "top" in q_lower:
            return sub_df.nlargest(n,"SolarGIS GHI")[['State','District','Substation','SolarGIS GHI']].reset_index(drop=True)
        if "highest" in q_lower:
            row = sub_df.loc[sub_df['SolarGIS GHI'].idxmax()]
            return show_row(row).to_frame().T.reset_index(drop=True)

    # ---------------- DISTRICT QUERIES ----------------
    if "district" in q_lower:
        dist_df = df[df['Type']=="district"]
        n = extract_top_n(q_lower)

        # State filter
        for state in df['State'].dropna().unique():
            if state.lower() in q_lower:
                state_df = dist_df[dist_df['State'].str.lower()==state.lower()]
                if "highest" in q_lower or "top" in q_lower:
                    return state_df.nlargest(n,"SolarGIS GHI")[['State','District','SolarGIS GHI']].reset_index(drop=True)

        if "top" in q_lower:
            return dist_df.nlargest(n,"SolarGIS GHI")[['State','District','SolarGIS GHI']].reset_index(drop=True)
        if "highest" in q_lower:
            row = dist_df.loc[dist_df['SolarGIS GHI'].idxmax()]
            return row[['State','District','SolarGIS GHI']].to_frame().T.reset_index(drop=True)

    # ---------------- SITE QUERIES ----------------
    if "site" in q_lower:
        site_df = df[df['Type']=="site"]
        n = extract_top_n(q_lower)

        # State filter
        for state in df['State'].dropna().unique():
            if state.lower() in q_lower:
                state_df = site_df[site_df['State'].str.lower()==state.lower()]
                if "highest" in q_lower or "top" in q_lower:
                    return state_df.nlargest(n,"SolarGIS GHI")[['State','District','Site','SolarGIS GHI']].reset_index(drop=True)

        if "top" in q_lower:
            return site_df.nlargest(n,"SolarGIS GHI")[['State','District','Site','SolarGIS GHI']].reset_index(drop=True)
        if "highest" in q_lower:
            row = site_df.loc[site_df['SolarGIS GHI'].idxmax()]
            return show_row(row).to_frame().T.reset_index(drop=True)

    # ---------------- STATE QUERIES ----------------
    if "state" in q_lower:
        state_avg = df.groupby("State")["SolarGIS GHI"].mean().reset_index()
        if "highest" in q_lower:
            row = state_avg.loc[state_avg['SolarGIS GHI'].idxmax()]
            return row.to_frame().T.reset_index(drop=True)
        if "top" in q_lower:
            n = extract_top_n(q_lower)
            return state_avg.nlargest(n,"SolarGIS GHI").reset_index(drop=True)
        if "average" in q_lower:
            return state_avg

    return "❓ Sorry, I couldn’t understand the query. Try again."


# --- Streamlit input ---
query = st.text_input("Ask a question about the solar dataset:")

# --- Query execution ---
if query:
    answer = answer_query(query)
    if isinstance(answer, pd.DataFrame):
        st.dataframe(answer.reset_index(drop=True), use_container_width=True)
    else:
        st.write(answer)
