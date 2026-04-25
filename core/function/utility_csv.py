async def func_api_file_to_obj_list(*, upload_file: any) -> list[dict[str, any]]:
    """Convert an uploaded CSV file into a list of dictionaries (all at once)."""
    import csv, io, asyncio
    def _parse_csv(file):
        return [row for row in csv.DictReader(io.TextIOWrapper(file, encoding="utf-8"))]
    obj_list = await asyncio.to_thread(_parse_csv, upload_file.file)
    await upload_file.close()
    return obj_list

async def func_api_file_to_chunks(*, upload_file: any, chunk_size: int) -> any:
    """Yield chunks of dictionaries from an uploaded CSV file for memory efficiency."""
    import csv, io, asyncio
    def _read_chunk(reader_iter, size):
        chunk = []
        try:
            for _ in range(size):
                chunk.append(next(reader_iter))
        except StopIteration:
            pass
        return chunk
    reader = csv.DictReader(io.TextIOWrapper(upload_file.file, encoding="utf-8"))
    reader_iter = iter(reader)
    while True:
        chunk = await asyncio.to_thread(_read_chunk, reader_iter, chunk_size)
        if not chunk:
            break
        yield chunk
    await upload_file.close()
    return
