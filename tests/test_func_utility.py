import pytest
from core.function.utility import func_file_extension_read, func_file_size_read, func_file_mime_read, func_converter_number, func_regex_check

# ===========================================================================
# func_file_extension_read
# ===========================================================================
def test_file_extension_txt():
    assert func_file_extension_read(filename="test.txt") == ".txt"

def test_file_extension_tar_gz():
    assert func_file_extension_read(filename="archive.tar.gz") == ".gz"

def test_file_extension_none():
    assert func_file_extension_read(filename="NO_EXTENSION") == ""

def test_file_extension_hidden():
    assert func_file_extension_read(filename=".gitignore") == ""

# ===========================================================================
# func_file_size_read
# ===========================================================================
def test_file_size_read_small(tmp_path):
    f = tmp_path / "small.txt"
    f.write_text("hello world")
    size = func_file_size_read(file_path=str(f))
    assert "B" in size

def test_file_size_read_nonexistent():
    assert func_file_size_read(file_path="nonexistent_file_xyz.bin") == "0 B"

# ===========================================================================
# func_file_mime_read
# ===========================================================================
def test_file_mime_read_txt():
    assert "text" in func_file_mime_read(filename="doc.txt")

def test_file_mime_read_json():
    assert "json" in func_file_mime_read(filename="data.json")

def test_file_mime_read_unknown():
    assert func_file_mime_read(filename="file.xyz123") == "application/octet-stream"

# ===========================================================================
# func_converter_number
# ===========================================================================
def test_converter_number_encode_decode_int():
    encoded = func_converter_number(type="int", mode="encode", x="hello")
    decoded = func_converter_number(type="int", mode="decode", x=encoded)
    assert decoded == "hello"

def test_converter_number_encode_decode_smallint():
    encoded = func_converter_number(type="smallint", mode="encode", x="ab")
    decoded = func_converter_number(type="smallint", mode="decode", x=encoded)
    assert decoded == "ab"

def test_converter_number_encode_decode_bigint():
    encoded = func_converter_number(type="bigint", mode="encode", x="hello.world")
    decoded = func_converter_number(type="bigint", mode="decode", x=encoded)
    assert decoded == "hello.world"

def test_converter_number_invalid_type():
    with pytest.raises(ValueError, match="invalid type"):
        func_converter_number(type="invalid", mode="encode", x="a")

def test_converter_number_too_long():
    with pytest.raises(ValueError, match="too long"):
        func_converter_number(type="smallint", mode="encode", x="toolong")

# ===========================================================================
# func_regex_check
# ===========================================================================
@pytest.mark.asyncio
async def test_regex_check_valid():
    config = {"username": ["^[a-z0-9_]{3,20}$", "bad username"]}
    await func_regex_check(config_regex=config, obj_list=[{"username": "valid_user"}])

@pytest.mark.asyncio
async def test_regex_check_invalid():
    config = {"username": ["^[a-z0-9_]{3,20}$", "bad username"]}
    with pytest.raises(Exception, match="bad username"):
        await func_regex_check(config_regex=config, obj_list=[{"username": "AB"}])

@pytest.mark.asyncio
async def test_regex_check_empty_config():
    await func_regex_check(config_regex={}, obj_list=[{"username": "anything"}])

@pytest.mark.asyncio
async def test_regex_check_field_not_present():
    config = {"email": ["^.+@.+$", "bad email"]}
    await func_regex_check(config_regex=config, obj_list=[{"username": "no_email_field"}])
