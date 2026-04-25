def func_gsheet_object_create(*, client_gsheet: any, sheet_url: str, obj_list: list) -> any:
    """Append records to a Google Sheet."""
    from urllib.parse import urlparse, parse_qs
    if not obj_list:
        return None
    parsed_url = urlparse(sheet_url)
    spreadsheet_id = parsed_url.path.split("/")[3]
    query_params = parse_qs(parsed_url.query)
    grid_id = int(query_params.get("gid", [""])[0])
    spreadsheet = client_gsheet.open_by_key(spreadsheet_id)
    worksheet = next((ws for ws in spreadsheet.worksheets() if ws.id == grid_id), None)
    if not worksheet:
        raise Exception("worksheet not found")
    column_headers = list(obj_list[0].keys())
    rows_to_insert = [[obj.get(col, "") for col in column_headers] for obj in obj_list]
    return worksheet.append_rows(rows_to_insert, value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS")

async def func_gsheet_object_read(*, sheet_url: str) -> list:
    """Read records from a public Google Sheet as a list of dictionaries."""
    from urllib.parse import urlparse, parse_qs
    import pandas as pd, aiohttp, io
    parsed_url = urlparse(sheet_url)
    spreadsheet_id = parsed_url.path.split("/d/")[1].split("/")[0]
    grid_id = parse_qs(parsed_url.query).get("gid", ["0"])[0]
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={grid_id}") as response:
            if response.status != 200:
                raise Exception(f"fetch failed: {response.status}")
            csv_content = await response.text()
    data_frame = pd.read_csv(io.StringIO(csv_content))
    return data_frame.where(pd.notnull(data_frame), None).to_dict(orient="records")
