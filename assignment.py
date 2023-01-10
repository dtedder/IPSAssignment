import logging
from bisect import bisect_left
from logging import StreamHandler, Formatter
from sys import stdout
from pandas import read_csv
from argparse import ArgumentParser

LOGGING_FORMATTER = Formatter('[%(asctime)s] [%(levelname)s] [%(name)s.%(funcName)s:%(lineno)d] %(message)s')


class Position:
	def __init__(self, log_time, x, y):
		self.log_time = log_time
		self.x = x
		self.y = y

	def __str__(self):
		return f"x:{self.x}, y:{self.y}, log_time:{self.log_time}"

class PositionFile:
	def __init__(self, path_to_csv):
		# use pandas to read the csv
		df = None
		df = read_csv(path_to_csv)

		# index the positions by their time as position objects
		self.positions = {}
		for f in range(len(df)):
			try:
				self.positions[df["t"][f]] = Position(df["t"][f], df["x"][f], df["y"][f])
			except Exception as ex:
				logging.warning(f"failed to parse row: {df.iloc[f]}, {ex}")

		# get a set of the times in order for searches
		self.ordered_times = sorted([f for f in self.positions])

		# fetch the envelope of the location set from the dataframe
		self.envelope = {
			"xmin": df["x"].min(),
			"ymin": df["y"].min(),
			"xmax": df["x"].max(),
			"ymax": df["y"].max(),
		}

class Reading:
	def __init__(self, log_time, accuracy):
		self.log_time = log_time
		self.accuracy = accuracy
		self.x = None
		self.y = None

	def __str__(self):
		return f"x:{self.x}, y:{self.y}, log_time:{self.log_time}"

	def set_position(self, pf: PositionFile):
		# check for out of bounds
		if self.log_time < pf.ordered_times[0] or self.log_time > pf.ordered_times[-1]:
			logging.error(f"unable to locate: {self.log_time}, out of bounds")
			return None

		# check for end coincident points
		for f in [0, -1]:
			if self.log_time == pf.ordered_times[f]:
				self.x = pf.positions[f].x
				self.y = pf.positions[f].y

		# find the locations inbetween the set where the time of the reading occurred
		location = bisect_left(pf.ordered_times, self.log_time)

		# check for last element
		if location >= len(pf.positions) - 1:
			location -= 1
		i = pf.positions[pf.ordered_times[location]]	
		k = pf.positions[pf.ordered_times[location + 1]]

		# interpolate between the surrounding points (formulae provided by assignment)
		#        Tj - Ti 
		#  Xj = --------- * (Xk - Xi) + Xi
		#        Tk - Ti
		#
		#        Tj - Ti
		#  Yj = --------- * (Yk - Yi) + Yi
		#        Tk - Ti
		scale_factor = (self.log_time - i.log_time) / (k.log_time - i.log_time)
		self.x = scale_factor * (k.x - i.x) + i.x
		self.y = scale_factor * (k.y - i.y) + i.y
		
class ReadingFile:
	def __init__(self, path_to_csv):
		df = read_csv(path_to_csv)
		self.readings = dict([(df["t"][f], Reading(df["t"][f], df["accuracy"][f])) for f in range(len(df))])


def perform_tasks():
	# verify command line parameters
	arg_parser = ArgumentParser(description="Processes a set of IPS recording files into a grid and completes tasks for the assignment")
	arg_parser.add_argument("mag_csv", help="full path to the csv file for the magnetics recording")
	arg_parser.add_argument("pos_csv", help="full path to the csv file for the positions recording")
	args = arg_parser.parse_args()

	positions = PositionFile(args.pos_csv)
	readings = ReadingFile(args.mag_csv)
	for time_stamp in readings.readings:
		reading = readings.readings[time_stamp]
		reading.set_position(positions)
		logging.info(reading)
	

if __name__ == "__main__":
	logger = logging.getLogger()
	stream_handler = StreamHandler(stdout)
	stream_handler.setFormatter(LOGGING_FORMATTER)
	stream_handler.setLevel(logging.INFO)
	logger.addHandler(stream_handler)
	logger.setLevel(logging.INFO)
	perform_tasks()
