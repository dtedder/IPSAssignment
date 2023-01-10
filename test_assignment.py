import pytest
from os.path import dirname
from assignment import PositionFile

def tf(sample_file_name):
	return f"{dirname(__file__)}/test_data/{sample_file_name}"

def test_PositionFile_file_not_found():
	with pytest.raises(FileNotFoundError):
		PositionFile(tf("this_wont_exist.csv"))

def test_PositionFile_valid_coulmns():
	pf = PositionFile(tf("pos_not_missing_columns.csv"))
	assert pf.positions is not None

def test_PositionFile_invalid_columns():
	pf = PositionFile(tf("pos_missing_column.csv"))
	with pytest.raises(AttributeError):
		print(pf.positions)
