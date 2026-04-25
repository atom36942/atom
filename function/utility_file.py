async def func_client_download_file(*, file_path: str, is_delete_after: int, chunk_size: int) -> any:
    """Stream a file for client download with optional automatic cleanup after transmission."""
    if "tmp/" not in str(file_path):
        raise Exception("IO Boundary Violation: tmp/ path required")
    from fastapi import responses
    from starlette.background import BackgroundTask
    import os, mimetypes, aiofiles
    file_name = os.path.basename(file_path)
    content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    async def file_iterator():
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    return responses.StreamingResponse(file_iterator(), media_type=content_type, headers={"Content-Disposition": f"attachment; filename=\"{file_name}\""}, background=BackgroundTask(os.remove, file_path) if is_delete_after == 1 else None)
def func_structure_create(*, directories: list, files: list) -> None:
    """Create directory and file structure if it doesn't exist."""
    import os
    for directory_path in directories:
        try:
            os.makedirs(directory_path, exist_ok=True)
        except OSError:
            pass
    for file_path in files:
        try:
            if not os.path.exists(file_path):
                open(file_path, "a").close()
        except OSError:
            pass
    return None

def func_folder_reset(*, folder_path: str) -> str:
    """Purge all files and subdirectories within a specified directory."""
    import os, shutil
    absolute_path = folder_path if os.path.isabs(folder_path) else os.path.join(os.getcwd(), folder_path)
    if not os.path.isdir(absolute_path):
        return "folder not found"
    for item in os.listdir(absolute_path):
        item_path = os.path.join(absolute_path, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
    return "folder reset done"
