def func_jira_worklog_export(*, url: str, email: str, api_token: str, start_date: str, end_date: str, output_path: str) -> str:
    """Export Jira worklogs for a specific period to a CSV file."""
    try:
        from jira import JIRA
        from pathlib import Path
        import pandas as pd
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        jira_client = JIRA(server=url, basic_auth=(email, api_token))
        log_rows = []
        people = set()
        jql = f"worklogDate >= '{start_date}' AND worklogDate <= '{end_date}'"
        all_issues = jira_client.enhanced_search_issues(jql, maxResults=0)
        for issue in all_issues:
            if getattr(issue.fields, "assignee", None):
                people.add(issue.fields.assignee.displayName)
            for worklog in jira_client.worklogs(issue.id):
                started_at = worklog.started[:10]
                if start_date <= started_at <= end_date:
                    author_name = worklog.author.displayName
                    people.add(author_name)
                    log_rows.append((author_name, started_at, worklog.timeSpentSeconds / 3600))
        date_range = pd.date_range(start=start_date, end=end_date).strftime("%Y-%m-%d").tolist()
        if not log_rows:
            if people:
                pd.DataFrame(index=sorted(list(people)), columns=date_range).fillna(0).astype(int).to_csv(output_path)
                return output_path
            pd.DataFrame(columns=date_range).to_csv(output_path)
            return output_path
        df = pd.DataFrame(log_rows, columns=["author", "date", "hours"])
        pivot = df.pivot_table(index="author", columns="date", values="hours", aggfunc="sum", fill_value=0).reindex(index=sorted(list(people)), columns=date_range, fill_value=0).round(0).astype(int)
        pivot.to_csv(output_path)
        return output_path
    except Exception as e:
        raise Exception(f"jira config exception: {str(e)}")
