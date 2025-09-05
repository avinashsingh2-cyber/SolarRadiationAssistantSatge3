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
def fuzzy_match(query, choices, limit=1, score_cutoff=82):
    query = query.strip().lower()
    norm_choices = {c.lower(): c for c in choices if isinstance(c, str) and c.strip() != ""}
    matches = process.extract(query, norm_choices.keys(), scorer=fuzz.WRatio, limit=limit)
    valid = [norm_choices[m[0]] for m in matches if m[1] >= score_cutoff]
    return valid

def fuzzy_match_best(query, choices):
    norm_choices = {c.lower(): c for c in choices if isinstance(c, str) and c.strip() != ""}
    match = process.extractOne(query.strip().lower(), norm_choices.keys(), scorer=fuzz.WRatio)
    if match:
        return norm_choices[match[0]], match[1]
    return None, 0

def extract_top_n(query):
    try:
        return int(re.findall(r"top (\\d+)", query)[0])
    except:
        return 5

def show_row(row):
    return row[['State','District','Substation','Site','SolarGIS GHI','Metonorm 8.2 GHI','Albedo']]

# --- Query handler ---
def answer_query(q):
    q_lower = q.strip().lower()

    # ---------- AUTO-DETECTION (fallback if no keywords) ----------
    best_type, best_name, best_score = None, None, 0

    name, score = fuzzy_match_best(q, df[df['Type']=="substation"]['Substation'].unique())
    if score > best_score:
        best_type, best_name, best_score = "substation", name, score

    name, score = fuzzy_match_best(q, df[df['Type']=="district"]['District'].unique())
    if score > best_score:
        best_type, best_name, best_score = "district", name, score

    name, score = fuzzy_match_best(q, df[df['Type']=="site"]['Site'].unique())
    if score > best_score:
        best_type, best_name, best_score = "site", name, score

    keywords = ["substation","district","site","state","ghi","radiation","top","average"]
    if best_score >= 82 and (not any(word in q_lower for word in keywords) or best_score >= 90):
        if best_type == "substation":
            sub_df = df[df['Type']=="substation"]
            return sub_df[sub_df['Substation']==best_name][['State','District','Substation','SolarGIS GHI','Metonorm 8.2 GHI','Albedo']]

        if best_type == "district":
            dist_df = df[df['Type']=="district"]
            return dist_df[dist_df['District']==best_name][['State','District','SolarGIS GHI','Albedo']]

        if best_type == "site":
            site_df = df[df['Type']=="site"]
            return site_df[site_df['Site']==best_name][['State','District','Site','SolarGIS GHI','Metonorm 8.2 GHI','Albedo']]

    # ---------- EXISTING LOGIC (keywords) ----------
    # ---------------- SUBSTATION QUERIES ----------------
    if "substation" in q_lower:
        sub_df = df[df['Type']=="substation"]

        if "radiation profile" in q_lower:
            name = re.findall(r"radiation profile of (.*) substation", q_lower)
            if name:
                matches = fuzzy_match(name[0], sub_df['Substation'].unique())
                if matches:
                    return sub_df[sub_df['Substation']==matches[0]][['State','District','Substation','SolarGIS GHI','Metonorm 8.2 GHI','Albedo']]

        if "ghi" in q_lower:
            name = re.findall(r"ghi(?: value)? of (.*) substation", q_lower)
            if name:
                matches = fuzzy_match(name[0], sub_df['Substation'].unique())
                if matches:
                    return sub_df[sub_df['Substation']==matches[0]][['State','District','Substation','SolarGIS GHI']]

        if "top" in q_lower:
            n = extract_top_n(q_lower)
            match = re.search(r"in (.+?) district", q_lower)
            if match:
                district = match.group(1).strip().title()
                result = sub_df[sub_df['District'].str.lower()==district.lower()].nlargest(n,"SolarGIS GHI")
                if not result.empty:
                    return result[['State','District','Substation','SolarGIS GHI']].reset_index(drop=True)

            for state in sub_df['State'].unique():
                if state.lower() in q_lower:
                    result = sub_df[sub_df['State'].str.lower()==state.lower()].nlargest(n,"SolarGIS GHI")
                    return result[['State','District','Substation','SolarGIS GHI']].reset_index(drop=True)

            return sub_df.nlargest(n,"SolarGIS GHI")[['State','District','Substation','SolarGIS GHI']].reset_index(drop=True)

    # ---------------- DISTRICT QUERIES ----------------
    if "district" in q_lower:
        dist_df = df[df['Type']=="district"]

        if "radiation profile" in q_lower:
            name = re.findall(r"radiation profile of (.*) district", q_lower)
            if name:
                matches = fuzzy_match(name[0], dist_df['District'].unique())
                if matches:
                    return dist_df[dist_df['District']==matches[0]][['State','District','SolarGIS GHI','Albedo']]

        if "ghi" in q_lower:
            name = re.findall(r"ghi(?: value)? of (.*) district", q_lower)
            if name:
                matches = fuzzy_match(name[0], dist_df['District'].unique())
                if matches:
                    return dist_df[dist_df['District']==matches[0]][['State','District','SolarGIS GHI']]

        if "top" in q_lower:
            n = extract_top_n(q_lower)
            avg = dist_df.groupby(["State","District"])["SolarGIS GHI"].mean().reset_index()

            if "each state" in q_lower or "every state" in q_lower:
                results = []
                for state in avg['State'].unique():
                    topn = avg[avg['State']==state].nlargest(n,"SolarGIS GHI")
                    results.append(topn)
                return pd.concat(results).reset_index(drop=True)

            for state in dist_df['State'].unique():
                if state.lower() in q_lower:
                    return avg[avg['State'].str.lower()==state.lower()].nlargest(n,"SolarGIS GHI").reset_index(drop=True)

            return avg.nlargest(n,"SolarGIS GHI").reset_index(drop=True)

        if "average" in q_lower:
            results = []
            for state in dist_df['State'].unique():
                if state.lower() in q_lower:
                    row = {"State": state}
                    if "ghi" in q_lower:
                        row["Average GHI"] = round(dist_df[dist_df['State'].str.lower()==state.lower()]["SolarGIS GHI"].mean(),2)
                    if "albedo" in q_lower:
                        row["Average Albedo"] = round(dist_df[dist_df['State'].str.lower()==state.lower()]["Albedo"].mean(),2)
                    results.append(row)
            if results:
                return pd.DataFrame(results)

    # ---------------- SITE QUERIES ----------------
    if "site" in q_lower:
        site_df = df[df['Type']=="site"]

        if "highest annual solar yield" in q_lower:
            row = site_df.loc[site_df['SolarGIS GHI'].idxmax()]
            return show_row(row).to_frame().T.reset_index(drop=True)

        if "radiation profile" in q_lower:
            name = re.findall(r"radiation profile of (.*) site", q_lower)
            if name:
                matches = fuzzy_match(name[0], site_df['Site'].unique())
                if matches:
                    return site_df[site_df['Site']==matches[0]][['State','District','Site','SolarGIS GHI','Metonorm 8.2 GHI','Albedo']]

        if "ghi" in q_lower:
            name = re.findall(r"ghi(?: value)? of (.*) site", q_lower)
            if name:
                matches = fuzzy_match(name[0], site_df['Site'].unique())
                if matches:
                    return site_df[site_df['Site']==matches[0]][['State','District','Site','SolarGIS GHI']]

        if "top" in q_lower:
            n = extract_top_n(q_lower)
            for state in site_df['State'].unique():
                if state.lower() in q_lower:
                    return site_df[site_df['State'].str.lower()==state.lower()].nlargest(n,"SolarGIS GHI")[['State','District','Site','SolarGIS GHI']].reset_index(drop=True)
            return site_df.nlargest(n,"SolarGIS GHI")[['State','District','Site','SolarGIS GHI']].reset_index(drop=True)

    # ---------------- STATE AVERAGES ----------------
    if "average" in q_lower and "state" in q_lower:
        if "ghi" in q_lower:
            return df.groupby("State")["SolarGIS GHI"].mean().reset_index()
        if "albedo" in q_lower:
            return df.groupby("State")["Albedo"].mean().reset_index()

    # ---------------- NEW ENHANCEMENTS ----------------
    # Highest / Top N states by GHI
    if "state" in q_lower and "ghi" in q_lower:
        state_avg = df.groupby("State")["SolarGIS GHI"].mean().reset_index()
        if "highest" in q_lower:
            row = state_avg.loc[state_avg['SolarGIS GHI'].idxmax()]
            return row.to_frame().T.reset_index(drop=True)
        if "top" in q_lower:
            n = extract_top_n(q_lower)
            return state_avg.nlargest(n,"SolarGIS GHI").reset_index(drop=True)

    # Highest / Top N districts
    if "district" in q_lower and ("highest" in q_lower or "top" in q_lower):
        dist_avg = df.groupby(["State","District"])["SolarGIS GHI"].mean().reset_index()
        if "highest" in q_lower:
            row = dist_avg.loc[dist_avg['SolarGIS GHI'].idxmax()]
            return row.to_frame().T.reset_index(drop=True)
        if "top" in q_lower:
            n = extract_top_n(q_lower)
            return dist_avg.nlargest(n,"SolarGIS GHI").reset_index(drop=True)

    # Highest / Top N substations
    if "substation" in q_lower and ("highest" in q_lower or "top" in q_lower):
        sub_df = df[df['Type']=="substation"]
        if "highest" in q_lower:
            row = sub_df.loc[sub_df['SolarGIS GHI'].idxmax()]
            return show_row(row).to_frame().T.reset_index(drop=True)
        if "top" in q_lower:
            n = extract_top_n(q_lower)
            return sub_df.nlargest(n,"SolarGIS GHI")[['State','District','Substation','SolarGIS GHI']].reset_index(drop=True)

    # Highest / Top N sites
    if "site" in q_lower and ("highest" in q_lower or "top" in q_lower):
        site_df = df[df['Type']=="site"]
        if "highest" in q_lower:
            row = site_df.loc[site_df['SolarGIS GHI'].idxmax()]
            return show_row(row).to_frame().T.reset_index(drop=True)
        if "top" in q_lower:
            n = extract_top_n(q_lower)
            return site_df.nlargest(n,"SolarGIS GHI")[['State','District','Site','SolarGIS GHI']].reset_index(drop=True)

    return "❓ Sorry, I couldn’t understand the query. Try again."

# --- Streamlit Input ---
query = st.text_input("Ask a question about the solar dataset:")
if query:
    answer = answer_query(query)
    if isinstance(answer, pd.DataFrame):
        st.dataframe(answer.reset_index(drop=True), use_container_width=True)
    else:
        st.write(answer)
