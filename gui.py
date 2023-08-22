#######################################################
# Imports #############################################
#######################################################
# Local
import tracer
from common import logger

# Normal
import os
import json
import sys
import sys
import pandas as pd
import multiprocessing as mp
from multiprocessing.pool import ThreadPool
import time
import typing

import PyQt5
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5.QtCore import *
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5.QtCore import QProcess

#######################################################
# Globals #############################################
#######################################################
DEFAULT_RESOLUTION = (1920, 1080)
CURRENT_RESOLUTION = None

#######################################################
# Functions #############################################
#######################################################
def sx(x):
	x_ratio = CURRENT_RESOLUTION[0] / DEFAULT_RESOLUTION[0]

	return int(x * x_ratio)
def sy(y):
	y_ratio = CURRENT_RESOLUTION[1] / DEFAULT_RESOLUTION[1]

	return int(y * y_ratio)

def geo(x, y, w, h):
	return QRect(sx(x), sy(y), sx(w), sy(h))

def sQSize(x, y):
	return QSize(sx(x), sy(y))

def addQRects(a: QRect, b: QRect):
	return QRect(a.x() + b.x(), a.y() + b.y(), a.width() + b.width(), a.height() + b.height())

def sanitizeComboBoxValue(text):
	if text == "" or text == "<None>":
		return None
	return text


def run(ips, outfolder):
	tracer.main(ips, outfolder)

#######################################################
# GUI Classes #########################################
#######################################################
# https://www.pythonguis.com/tutorials/pyqt-layouts/

class CSVImportWindow(QMainWindow):
	def __init__(self, root, filepath):
		super().__init__()
		self.root = root
		self.filepath = filepath
		(WIDTH, HEIGHT) = 1200, 800
		self.resize(sQSize(WIDTH, HEIGHT))

		self.layout = QVBoxLayout()

		self.column_label = QLabel("What column has the destinations?", self)
		self.column_label.setAlignment(Qt.AlignCenter)
		self.column_label.setStyleSheet(" color: black")
		self.column_label.setFont(QFont('Arial:Bold', 25))
		#self.column_label.setGeometry(geo(0, 0, WIDTH / 4, HEIGHT / 4))
		self.layout.addWidget(self.column_label)

		self.column_combobox = QComboBox(self)
		self.column_combobox.setFont(QFont("Arial", 12))
		#self.column_combobox.setGeometry(addQRects(self.state_label.geometry(), geo(0, LABEL_HEIGHT + MARGIN, 0, 0)))
		self.layout.addWidget(self.column_combobox)

		# self.city_box.currentIndexChanged.connect(self.onCityChanged)
		# self.city_box.clear()
		# 			self.city_box.addItems(self.NONE + cities)

		self.mdi = QMdiArea(self)
		# self.mdi.setGeometry(geo(WIDTH * 2/4, 50, WIDTH * 2/4, HEIGHT))
		self.layout.addWidget(self.mdi)

		# Create buttons
		self.button_layout = QHBoxLayout()
		self.button_layout.setSpacing(500)

		# Manually
		self.import_button = QPushButton("Import", self)
		self.import_button.setFont(QFont('Arial:Bold', 20))
		self.import_button.setStyleSheet("background-color: rgb(188,36,36); color: white")
		self.import_button.clicked.connect(self.accept)
		self.button_layout.addWidget(self.import_button)

		# Import file
		self.cancel_button = QPushButton("Cancel", self)
		self.cancel_button.setFont(QFont('Arial:Bold', 20))
		self.cancel_button.setStyleSheet("background-color: rgb(188,36,36); color: white")
		self.cancel_button.clicked.connect(self.close)
		self.button_layout.addWidget(self.cancel_button)

		self.layout.addLayout(self.button_layout)
		container = QWidget()
		container.setLayout(self.layout)
		self.setCentralWidget(container)

		self.loadCSV(filepath)

	def loadCSV(self, filepath):
		self.df = pd.read_csv(filepath)

		self.column_combobox.addItems(list(self.df.columns))

		self.model = TableModel(self.df)
		self.table = QtWidgets.QTableView()
		self.table.setModel(self.model)
		self.table.show()
		self.mdi.addSubWindow(self.table)
		self.mdi.tileSubWindows()

		"""
		self.model = TableModel(df)
		self.table = QtWidgets.QTableView()
		self.table.setModel(self.model)
		self.table.show()

		self.layout = QtWidgets.QBoxLayout(2)
		self.layout.addWidget(self.table)
		self.docked = QtWidgets.QDockWidget()
		self.dockedWidget = QtWidgets.QWidget()
		self.docked.setWidget(self.dockedWidget)
		self.dockedWidget.setLayout(self.layout)
		self.docked.setWindowTitle("Statistics")
		self.docked.show()

		dockedWindow = QMdiSubWindow()
		dockedWindow.setLayout(self.layout)
		self.mdi.addSubWindow(dockedWindow)
		dockedWindow.setWindowTitle("Docked Window")
		dockedWindow.setWidget(self.docked)
		dockedWindow.show()

		self.mdi.tileSubWindows()
		"""

	def accept(self):
		self.root.addTargetsToProcess(tracer.get_IPs_from_file(self.filepath, column=self.column_combobox.currentText()))
		self.close()

class InputWindow(QMainWindow):
	def __init__(self, root):
		super().__init__()
		self.root = root

		self.setWindowTitle("Input Window")
		(WIDTH, HEIGHT) = 900, 400
		self.resize(sQSize(WIDTH, HEIGHT))

		MARGIN = 10
		LABEL_WIDTH = (WIDTH / 3) - MARGIN
		LABEL_HEIGHT = 25

		self.NONE = ["<None>"]

		self.header_label = QLabel("How do you want to add inputs?", self)
		self.header_label.setStyleSheet(" color: black")
		self.header_label.setAlignment(Qt.AlignCenter)
		self.header_label.setFont(QFont('Arial:Bold', 25))
		self.header_label.setGeometry(geo(0, 0, WIDTH, HEIGHT/4))

		self.secondary_label = QLabel("You can import files containing destinations or add targets manually.", self)
		self.secondary_label.setStyleSheet(" color: black")
		self.secondary_label.setAlignment(Qt.AlignCenter)
		self.secondary_label.setFont(QFont('Arial:Bold', 18))
		self.secondary_label.setGeometry(addQRects(self.header_label.geometry(), geo(0, 12.5 + 9, 0, 0)))

		# Create buttons
		self.button_layout = QHBoxLayout()
		self.button_layout.setSpacing(50)

		# Manually
		self.manual_button = QPushButton("Manual", self)
		self.manual_button.setFont(QFont('Arial:Bold', 20))
		self.manual_button.setStyleSheet("background-color: rgb(188,36,36); color: white")
		self.button_layout.addWidget(self.manual_button)


		# Import file
		self.file_button = QPushButton("Select File", self)
		self.file_button.setFont(QFont('Arial:Bold', 20))
		self.file_button.setStyleSheet("background-color: rgb(188,36,36); color: white")
		self.file_button.clicked.connect(self.promptForFile)
		self.button_layout.addWidget(self.file_button)

		button_container = QWidget(self)
		button_container.setLayout(self.button_layout)
		button_container.setStyleSheet(" color: black; background: rgba(76, 175, 80, 0);")
		button_container.setGeometry(geo(0, HEIGHT - 90, WIDTH, 90))


		#self.state_box = QComboBox(self)
		#self.state_box.setFont(QFont("Arial", 12))
		#self.state_box.setGeometry(addQRects(self.state_label.geometry(), geo(0, LABEL_HEIGHT + MARGIN, 0, 0)))
		#self.state_box.setDisabled(True)

		"""
		# City section
		self.city_label = QLabel("City", self)
		self.city_label.setAlignment(Qt.AlignCenter)
		self.city_label.setStyleSheet(" color: black; background-color: #444488;")
		self.city_label.setFont(QFont('Arial:Bold', 20))
		self.city_label.setGeometry(geo(LABEL_WIDTH*2 + MARGIN*3 / 1.3, HEIGHT / 4, LABEL_WIDTH, LABEL_HEIGHT))

		self.city_box = QComboBox(self)
		self.city_box.setFont(QFont("Arial", 12))
		self.city_box.setGeometry(addQRects(self.city_label.geometry(), geo(0, LABEL_HEIGHT + MARGIN, 0, 0)))
		self.city_box.setDisabled(True)

		# Buttons
		self.cancel_button = QPushButton("Cancel", self)
		#self.cancel_button.setGeometry(addQRects(self.cc_label.geometry(), geo(MARGIN, HEIGHT/2, -MARGIN*2, MARGIN*2)))
		self.cancel_button.setFont(QFont('Arial:Bold', 20))
		self.cancel_button.setStyleSheet("background-color: rgb(188,36,36); color: white")

		self.clear_button = QPushButton("Clear Inputs", self)
		#self.clear_button.setGeometry(addQRects(self.state_label.geometry(), geo(MARGIN, HEIGHT / 2, -MARGIN*2, MARGIN * 2)))
		self.clear_button.setFont(QFont('Arial:Bold', 20))
		self.clear_button.setStyleSheet("background-color: rgb(188,36,36); color: white")

		self.run_button = QPushButton("Run", self)
		#self.run_button.setGeometry(addQRects(self.city_label.geometry(), geo(MARGIN, HEIGHT / 2, -MARGIN*2, MARGIN * 2)))
		self.run_button.setFont(QFont('Arial:Bold', 20))
		self.run_button.setStyleSheet("background-color: rgb(188,36,36); color: white")

		# Do setup stuff

		self.cancel_button.clicked.connect(self.onCancelClicked)
		#self.clear_button.clicked.connect(self.onClearClicked)
		self.run_button.clicked.connect(self.onRunClicked)
		"""

	def onCancelClicked(self):
		self.close()

	def promptForFile(self):
		# https://doc.qt.io/qtforpython-5/PySide2/QtWidgets/QFileDialog.html#detailed-description
		# https://doc.qt.io/qtforpython-5/PySide2/QtWidgets/QFileDialog.html#PySide2.QtWidgets.PySide2.QtWidgets.QFileDialog.getOpenFileName

		filepath, _filter = QFileDialog.getOpenFileName(self,
														"Import URL list",
														filter="Any file (*);;Comma-separated value file (*.csv);;Normal text file (*.txt)",
														initialFilter="Comma-separated value file (*.csv)"
														)

		if filepath == "":
			# No file selected.
			logger.info("No file was selected in promptForFile.")
			return
		else:
			filetype = os.path.splitext(filepath)[1]
			if filetype == ".csv":
				self.root._csvimportwindow = CSVImportWindow(self.root, filepath)
				self.root._csvimportwindow.show()
			else:
				self.root.addTargetsToProcess(tracer.get_IPs_from_file(filepath))

			self.close()

		pass

	def onRunClicked(self):
		self.close()

		self.root.mdi.closeAllSubWindows()


# https://www.pythonguis.com/tutorials/qtableview-modelviews-numpy-pandas/

class TableModel(QtCore.QAbstractTableModel):
	def __init__(self, data):
		super(TableModel, self).__init__()
		self._data = data

	def data(self, index, role):
		if role == Qt.DisplayRole:
			value = self._data.iloc[index.row(), index.column()]
			return str(value)

	def rowCount(self, index):
		return self._data.shape[0]

	def columnCount(self, index):
		return self._data.shape[1]

	def headerData(self, section, orientation, role):
		# section is the index of the column/row.
		if role == Qt.DisplayRole:
			if orientation == Qt.Horizontal:
				return str(self._data.columns[section])

			if orientation == Qt.Vertical:
				return str(self._data.index[section])

class MyDialog(QDialog):

	# I don't know why this has to be declared here.
	# Went from https://stackoverflow.com/questions/36434706/pyqt-proper-use-of-emit-and-pyqtsignal
	# to...
	# https://stackoverflow.com/questions/17578428/pyqt5-signals-and-slots-qobject-has-no-attribute-error
	onClick = pyqtSignal(str, name="onClick")

	def __init__(self, parent, buttons):
		super().__init__(parent)

		self.setWindowTitle("Traceroute program")
		self.layout = QVBoxLayout()

		# https://doc.qt.io/qtforpython-5/PySide2/QtWidgets/QDialogButtonBox.html#PySide2.QtWidgets.PySide2.QtWidgets.QDialogButtonBox.StandardButton
		self.message_label = QLabel("<msg>")
		self.layout.addWidget(self.message_label)

		self.button_box = QDialogButtonBox(buttons)
		# self.button_box.accepted.connect(self.close)
		dialogClick: typing.Callable[[QPushButton], None] = lambda btn: self.onClick.emit(btn.text())
		self.button_box.clicked.connect(dialogClick)

		self.layout.addWidget(self.button_box)
		self.setLayout(self.layout)


	def setMessage(self, msg: str):
		self.message_label.setText(msg)



class Window(QMainWindow):
	def __init__(self):
		global CURRENT_RESOLUTION
		super().__init__()

		# Screen stuff
		screen = App.primaryScreen()
		self.screen_size = (screen.size().width(), screen.size().height())
		CURRENT_RESOLUTION = self.screen_size

		# Main Window
		self.setWindowTitle("Traceroute")

		# Area for subwindows
		self.mdi = QMdiArea(self)
		self.mdi.setGeometry(geo(800, 50, 1060, DEFAULT_RESOLUTION[1] - 100))

		# UI
		self.buttons = []
		self.UIComponents()

		self.showFullScreen()

	def UIComponents(self):
		"""
		#bannerg
		red_bar = QLabel("You cant see me", self)
		red_bar.setStyleSheet("background-color: rgb(163,4,4); color: rgb(163,4,4)")
		red_bar.setGeometry(25, 25, 725, 275)
		"""
		# BU logo
		self.logo = QLabel(self)

		BUTTON_SIZE = sQSize(400, 75)

		self.pixmap = QPixmap('assets/biggerBlogo.png')
		#self.resizedLabel = self.pixmap.scaled(700 , 700, Qt.KeepAspectRatio, Qt.FastTransformation)
		self.logo.setPixmap(self.pixmap)
		self.logo.resize(sx(800), sy(400))
		self.logo.setAlignment(Qt.AlignCenter)

		# Buttons

		"""
		self.stats_button = QPushButton("% Statistics", self)
		# self.stats.setGeometry(geo(195, 630, 400, 75))
		self.stats_button.resize(BUTTON_SIZE)
		# self.stats.setIcon(QtGui.QIcon("assets/exGraph.png"))
		self.stats_button.setStyleSheet("background-color:rgb(188,36,36); color: white")
		self.stats_button.setFont(QFont('Arial:Bold', 24))
		self.stats_button.setIconSize(sQSize(500, 500))
		self.stats_button.clicked.connect(self.statsPress)
		"""

		self.menu_button_container = QWidget(self)
		
		self.button_layout = QVBoxLayout()

		self.add_input_button = QPushButton("Add Inputs")
		self.add_input_button.setMinimumSize(BUTTON_SIZE)
		#self.add_input_button.setIcon(QtGui.QIcon("assets/readme.png"))
		#self.add_input_button.setStyleSheet("background-color:rgb(188,36,36); color: white")
		self.add_input_button.setFont(QFont('Arial:Bold', 24))
		self.add_input_button.setIconSize(sQSize(500, 500))
		self.add_input_button.clicked.connect(self.addInputPressed)
		self.button_layout.addWidget(self.add_input_button)

		self.run_button = QPushButton("Run", self)
		self.run_button.setMinimumSize(BUTTON_SIZE)
		# self.run_button.setIcon(QtGui.QIcon("assets/readme.png"))
		# self.run_button.setStyleSheet("background-color:rgb(188,36,36); color: white")
		self.run_button.setFont(QFont('Arial:Bold', 24))
		self.run_button.setIconSize(sQSize(500, 500))
		self.run_button.clicked.connect(self.runPressed)
		self.button_layout.addWidget(self.run_button)

		self.close_windows_button = QPushButton("Close All Windows", self)
		self.close_windows_button.setMinimumSize(BUTTON_SIZE)
		self.close_windows_button.setStyleSheet("background-color: rgb(188,36,36); color: white")
		self.close_windows_button.setFont(QFont('Arial:Bold', 24))
		self.close_windows_button.clicked.connect(self.closePress)
		self.button_layout.addWidget(self.close_windows_button)

		self.exit_button = QPushButton("Exit", self)
		self.exit_button.setMinimumSize(BUTTON_SIZE)
		self.exit_button.setStyleSheet("background-color: rgb(188,36,36); color: white")
		self.exit_button.setFont(QFont('Arial:Bold', 24))
		self.exit_button.clicked.connect(self.exitPress)
		self.button_layout.addWidget(self.exit_button)


		# I don't know if changing to this layout was worth the frustration here compared to the position math I had before.
		self.menu_button_container.setStyleSheet("background-color: #cccccc;")
		self.menu_button_container.setGeometry(geo(195, 500, 400, (75 + 20) * 4))  # Using the raw 400 and 75 to avoid double scaling
		self.menu_button_container.setLayout(self.button_layout)

		self.ips_df = pd.DataFrame(columns=["targets"])
		self.ips_df.loc[0, self.ips_df.columns] = ["1.1.1.1"]  # Test IP

		self.model = TableModel(self.ips_df)
		self.table = QtWidgets.QTableView()
		self.table.setModel(self.model)
		self.table.show()
		self.mdi.addSubWindow(self.table)
		self.mdi.tileSubWindows()

	def addTargetsToProcess(self, targets: list[str]):
		# Well... this is all pretty ugly.
		self.ips_df["targets"] = list(set(list(self.ips_df["targets"]) + targets))
		self.model.removeRows(0, self.model.rowCount(0))
		# Doing these two steps seems like the fastest way of rebuilding the table but not sure if there are any side effects.
		self.model.__init__(self.ips_df)
		self.table.setModel(self.model)

	def addInputPressed(self):
		self.input_window = InputWindow(self)
		self.input_window.show()

	def runPressed(self):
		if len(self.ips_df.index) == 0:
			dialog = MyDialog(self, QDialogButtonBox.Ok)
			dialog.setWindowTitle("Error")
			dialog.setMessage("You need to have some targets to traceroute.")
			dialog.onClick.connect(dialog.close)
			dialog.exec()
			return

		output_directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
		if output_directory == "":
			logger.info("Output directory was not selected from QFileDialog")

			dialog = MyDialog(self, QDialogButtonBox.Ok | QDialogButtonBox.Discard)
			dialog.setWindowTitle("Output folder warning")
			dialog.setMessage("You need to select an output folder for the results to be saved to.\nIf you select to discard the results, the program will run but will not save anything.")
			dialog.onClick.connect(dialog.close)
			dialog.onClick.connect(lambda txt: txt != "OK" and self.runTracer(None))  # I guess OK is uppercase in the dialog.

			dialog.exec()

			return
		else:
			self.runTracer(output_directory)

	def runTracer(self, outfolder):
		logger.info(f"runTracer called with outfolder={outfolder}")
		ips = list(self.ips_df["targets"])
		#run(ips, outfolder)

	def statsPress(self, chart, stats):
		chart_path = chart
		self.graph = QLabel(self)
		self.pie_chart = QPixmap(chart_path)
		self.graph.setPixmap(self.pie_chart)
		self.graph.show()

		#### https://www.pythonguis.com/tutorials/qtableview-modelviews-numpy-pandas/
		statisticsPath = stats
		dataframe = pd.read_csv(statisticsPath)
		self.model = TableModel(dataframe)
		self.table = QtWidgets.QTableView()
		self.table.setModel(self.model)
		self.table.show()

		self.layout = QtWidgets.QBoxLayout(2)
		self.layout.addWidget(self.graph)
		self.layout.addWidget(self.table)
		self.docked = QtWidgets.QDockWidget()
		self.dockedWidget = QtWidgets.QWidget()
		self.docked.setWidget(self.dockedWidget)
		self.dockedWidget.setLayout(self.layout)
		self.docked.setWindowTitle("Statistics")
		self.docked.show()

		dockedWindow = QMdiSubWindow()
		dockedWindow.setLayout(self.layout)
		self.mdi.addSubWindow(dockedWindow)
		dockedWindow.setWindowTitle("Docked Window")
		dockedWindow.setWidget(self.docked)
		dockedWindow.show()

		self.mdi.tileSubWindows()

	def readPress(self):
		readWin = QMdiSubWindow()
		readWin.setWindowTitle("README")
		self.mdi.addSubWindow(readWin)
		readWin.show()

		widget = QLabel("Instructions:\nPress the Add/Remove Inputs button. You will be prompted to input the Country Code, State, \nand City to narrow down the location where you want statistics on RPKI implementation.\n\nNext press the Run button to run the program with the inputs that you have given.\n\nTo view the statistics of the inputs, press the Statistics button.\n\nTo view example graphs from Gephi, please press the Example Graphs button to view it.\n\nThe RPKI statistics displayed was scraped from NIST:\nhttps://rpki-monitor.antd.nist.gov/RPKI")
		font = widget.font()
		font.setPointSize(15)
		widget.setFont(font)
		widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
		readWin.setWidget(widget)
		self.mdi.tileSubWindows()

	def closePress(self):
		self.mdi.closeAllSubWindows()

	def exitPress(self):
		QApplication.closeAllWindows()
		self.close()

	def onRunFinish(self):
		print("Run finished")



if __name__ == "__main__":
	App = QApplication(sys.argv)

	window = Window()
	window.show()

	sys.exit(App.exec())
