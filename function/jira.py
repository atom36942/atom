"""Atom jira functions."""

async def func_jira_worklog_export(*, url: str, email: str, api_token: str, start_date: str, end_date: str) -> str:
    """Exports Jira worklogs within a date range to a CSV file and returns the file path."""
    import os
    import uuid
    import asyncio
    import pandas as pd
    from jira import JIRA
    os.makedirs("tmp", exist_ok=True)
    output_path = f"tmp/{uuid.uuid4().hex}.csv"
    def _export():
        jira = JIRA(server=url, basic_auth=(email, api_token))
        log_rows, people = [], set()
        for issue in jira.enhanced_search_issues(f"worklogDate >= '{start_date}' AND worklogDate <= '{end_date}'", maxResults=0):
            if getattr(issue.fields, "assignee", None): people.add(issue.fields.assignee.displayName)
            for w in jira.worklogs(issue.id):
                if start_date <= w.started[:10] <= end_date:
                    people.add(w.author.displayName)
                    log_rows.append((w.author.displayName, w.started[:10], w.timeSpentSeconds / 3600))
        cols = pd.date_range(start_date, end_date).strftime("%Y-%m-%d").tolist()
        df = pd.DataFrame(log_rows, columns=["author", "date", "hours"])
        if not df.empty: df = df.pivot_table(index="author", columns="date", values="hours", aggfunc="sum", fill_value=0)
        df.reindex(index=sorted(people), columns=cols, fill_value=0).round(0).astype(int).to_csv(output_path)
        return output_path
    await asyncio.to_thread(_export)
    return output_path
