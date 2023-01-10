import unittest

from assignment import PositionFile

class TestMain(unittest.TestCase):
	def check_file_input(self):
		with self.assertRaises(FileNotFoundError):
			PositionFile("/Users/doug/file_doesnt_exits.csv")

if __name__ == "__main__":
	unittest.main()
