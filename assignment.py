import logging
from bisect import bisect_left
from logging import StreamHandler, Formatter
from sys import stdout
from time import sleep
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

		# ensure the required columns are present
		if len({"t","x","y"}.difference(df.columns)) != 0:
			logging.error("required columns not present")
			return

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
		self.row = None
		self.col = None

	def __str__(self):
		return f"x:{self.x}, y:{self.y}, log_time:{self.log_time}"

	def bin_id(self):
		return f"{self.row}_{self.col}"

	def set_position(self, pf: PositionFile):
		# check for out of bounds
		if self.log_time < pf.ordered_times[0] or self.log_time > pf.ordered_times[-1]:
			logging.error(f"unable to locate: {self.log_time}, out of bounds")
			return

		# check for end coincident points
		for f in [0, -1]:
			if self.log_time == pf.ordered_times[f]:
				self.x = pf.positions[f].x
				self.y = pf.positions[f].y

		# # find the locations inbetween the set where the time of the reading occurred
		location = bisect_left(pf.ordered_times, self.log_time)

		# # check for last element
		i = pf.positions[pf.ordered_times[location - 1]]	
		k = pf.positions[pf.ordered_times[location]]
		logging.debug(f"between: {location -  1} and {location}")

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
		self.bins = {}
		self.max_row = -1
		self.max_col = -1

	def bin_readings(self, xmin, ymin, cell_size):
		for ts in self.readings:
			f = self.readings[ts]
			try:
				f.col = int((f.x - xmin) / cell_size)
				f.row = int((f.y - ymin) / cell_size)
				if f.bin_id() not in self.bins:
					self.bins[f.bin_id()] = []
				self.bins[f.bin_id()].append(f)

				# set the bounds for drawing the map
				if f.col > self.max_col:
					self.max_col = f.col
				if f.row > self.max_row:
					self.max_row = f.row

			except Exception as ex:
				logging.warning(f"unable to bin reading: {f}")

	def get_symbol_for_bin_id(self, bin_id):
		size_bin = len(self.bins[bin_id]) if bin_id in self.bins else 0
		if size_bin < 1:
			return "  "
		if size_bin < 25:
			return " 1"
		if size_bin < 50:
			return " 2"
		if size_bin < 100:
			return " 3"
		if size_bin < 150:
			return " 4"
		return " 5"

	def plot_bins(self):
		print(f"+{(self.max_col + 1) * 2 * '-'}+")
		for row in range(self.max_row, -1, -1):
			grid_line = "|"
			for col in range(self.max_col + 1):
				grid_line = "{}{}".format(grid_line, self.get_symbol_for_bin_id(f"{row}_{col}"))
			grid_line = f"{grid_line}|"
			print(grid_line)
		print(f"+{(self.max_col + 1) * 2 * '-'}+")

def main(cell_size=5):
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

	# cover the area of the points from top left to bottom right
	minimum_buffer_distance = cell_size / 2.0
	xmin = positions.envelope["xmin"] - minimum_buffer_distance
	xmax = xmin
	while (xmax <= positions.envelope["xmax"] + minimum_buffer_distance):
		xmax += cell_size
	ymax = positions.envelope["ymax"] + minimum_buffer_distance
	ymin = ymax
	while (ymin > positions.envelope["ymin"] - minimum_buffer_distance):
		ymin -= cell_size

	# group all the readings into bins by count
	# for some reason i cannot find any signal strength on the magnetic file so just count them
	readings.bin_readings(xmin, ymin, 5)
	readings.plot_bins()
	# with open("/Users/doug6376/Desktop/test.csv", "w") as output:
	# 	output.write("x,y,t\n")
	# 	for ts in readings.readings:
	# 		f = readings.readings[ts]
	# 		output.write(f"{f.x},{f.y},{f.log_time}\n")
	

if __name__ == "__main__":
	logger = logging.getLogger()
	stream_handler = StreamHandler(stdout)
	stream_handler.setFormatter(LOGGING_FORMATTER)
	stream_handler.setLevel(logging.INFO)
	logger.addHandler(stream_handler)
	logger.setLevel(logging.INFO)
	main()
