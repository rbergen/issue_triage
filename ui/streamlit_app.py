import os, httpx, streamlit as st
API = os.getenv("API_URL", "http://api:8000")

st.set_page_config(page_title="Issue Triage Copilot", layout="wide")

st.title("Issue Triage Copilot")

st.header("Semantic Search")
q = st.text_input("Query")
repo = st.text_input("Repo filter (owner/name)")
if st.button("Search") and q:
    with httpx.Client() as c:
        r = c.get(f"{API}/search/", params={"q": q, "repo": repo or None})
        r.raise_for_status()
        data = r.json()["items"]
        for item in data:
            st.write(f"**{item['title'] or '(no title)'}** — {item['repo']}  ")
            st.write(item["snippet"])
            st.write(item["url"])
            st.write(f"score: {item['score']:.4f}")
            st.divider()

st.header("New Issue Triage")
col1, col2 = st.columns(2)
with col1:
    t = st.text_input("Issue title")
with col2:
    b = st.text_area("Issue body")
repo2 = st.text_input("Repo (optional)", key="repo2")
if st.button("Suggest Duplicates") and (t or b):
    with httpx.Client() as c:
        r = c.post(f"{API}/triage/", json={"title": t, "body": b, "repo": repo2 or None})
        r.raise_for_status()
        data = r.json()
        st.subheader("Candidates")
        for cnd in data["candidates"]:
            st.write(f"**{cnd['title'] or '(no title)'}**  ")
            st.write(cnd["snippet"])
            st.write(cnd["url"])
            st.write(f"score: {cnd['score']:.4f}")
            st.divider()
        st.subheader("Draft Reply")
        st.write(data["draft_reply"])

st.header("Q&A")
q2 = st.text_input("Your question", key="q2")
repo3 = st.text_input("Repo (optional)", key="repo3")
if st.button("Ask") and q2:
    with httpx.Client() as c:
        r = c.post(f"{API}/qa/", json={"question": q2, "repo": repo3 or None})
        r.raise_for_status()
        data = r.json()
        st.write(data["answer"])
        if data.get("citations"):
            st.write("Citations:")
            for i, u in enumerate(data["citations"], start=1):
                st.write(f"[{i}] {u}")