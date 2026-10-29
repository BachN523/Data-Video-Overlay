from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from pyqtLE import *
from DataVideoOverlayBackend import backendMain
from LE import *
import sys, csvParser

class MainWindow(QWidget):
    # This class' main purpose is to draw the main window and its associated functionality
    
    def __init__(self):
        # general initilization. Draws what the program looks like before you create or load a file
        
        super().__init__()

        versionNumber = "Beta"

        self.setWindowTitle(f'Data Video Overlay {versionNumber}')

        self.setWindowIcon(QIcon("TempIco.png"))

        self.layout = QVBoxLayout(self)


        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()

        
        self.tabs.addTab(self.tab1, "Video")
        self.tabs.addTab(self.tab2, "Data")
        self.tabs.addTab(self.tab3, "Optional")
        

        self.tab1.layout = QGridLayout(self)

        progressBar = QProgressBar()

        progressBar.setRange(0,100)

        progressBar.setValue(0)

        saveButton = PushButtonLE('Save', clicked=lambda: self.saveButtonClicked())

        self.tab1.setLayout(self.makeTabOne())

        self.tab2.setLayout(self.makeTabTwo())

        self.layout.addWidget(progressBar)
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(saveButton)

        self.setLayout(self.layout)

    def makeTabOne(self):
        tabOneLayout = QGridLayout()

        self.videoPath = TextEditLE()
        self.videoPath.setPlaceholderText("Path to video")

        pathOneSelect = PushButtonLE('...')
        pathOneSelect.clicked.connect(lambda _: self.loadFileButton(self.videoPath,1))

        # The below blocked out function dynamically creates radio buttons 
        # -------------------------------------------------------

        typeButtonGroup = QButtonGroup()


        # This function defines how many buttons are created. Index #,0 defines what gets written to the file
        # Index #,1 defines what gets displayed on the screen
        types = ["Accel","AutoX","Skid Pad","Enduro"]

        typeRadioButtons = []
        radioLayout1 = QHBoxLayout()

        typeCounter = 0
        while len(typeRadioButtons) < len(types):
            #creates the actual button and adds it to an array
            typeRadioButton = QRadioButton(f"{types[typeCounter]}")
            typeButtonGroup.addButton(typeRadioButton)
            typeRadioButtons.append(typeRadioButton)

            typeCounter += 1
        
        
        # this adds the buttons created above to the layout

        for i in typeRadioButtons:
            
            radioLayout1.addWidget(i)

        radioWidget1 = QWidget()
        radioWidget1.setLayout(radioLayout1)

        # -------------------------------------------------------

        tabOneLayout.addWidget(self.videoPath,0,0)

        tabOneLayout.addWidget(pathOneSelect,0,1)

        tabOneLayout.addWidget(radioWidget1,1,0)

        return tabOneLayout

    def makeTabTwo(self):
        fileLoaded = False
        tabTwoLayout = QGridLayout()

        def loadCSVLayout(tabTwoLayout):

            self.csvPath = TextEditLE()
            self.csvPath.setPlaceholderText("Path to CSV")

            pathOneSelect = PushButtonLE('...')
            pathOneSelect.clicked.connect(lambda _: self.loadFileButton(self.csvPath,0))


            parseButton = PushButtonLE('Parse')
            parseButton.clicked.connect(lambda _, tabTwoLayout=tabTwoLayout: displayCSVOptions(tabTwoLayout, self.csvPath.toPlainText()))


            tabTwoLayout.addWidget(self.csvPath,0,0)

            tabTwoLayout.addWidget(pathOneSelect,0,1)

            tabTwoLayout.addWidget(parseButton,1,0,1,2)


        def displayCSVOptions(tabTwoLayout, fileLocation):
            # parse() returns a list of dicts mapping channel name -> list of values
            # TODO: parse() currently returns hardcoded test data; update this once it reads the real CSV
            returnedData = csvParser.parse(fileLocation)

            channels = []
            for i in returnedData:
                for channel in i:
                    if channel not in channels:
                        channels.append(channel)

            # Rows 0 and 1 are the path box and parse button
            for row, channel in enumerate(channels, start=2):
                tabTwoLayout.addWidget(QCheckBox(channel),row,0,1,2)


        if fileLoaded:
            displayCSVOptions(tabTwoLayout)
        else:
            loadCSVLayout(tabTwoLayout)
            fileLoaded == True



        #tabTwoLayout.addWidget(radioWidget1,1,0)

        return tabTwoLayout

    def saveButtonClicked(self):
        # Runs the backend with the selected files and shows the [title, message] it returns
        result = backendMain(self.csvPath.toPlainText(), self.videoPath.toPlainText())

        msg = QMessageBox()
        msg.setWindowTitle(result[0])
        msg.setText(result[1])
        msg.exec()

    def loadFileButton(self, textBox, fileTypeIndex):
        # loads the file and ensures the data is somewhat valid
        print(textBox)

        options = QFileDialog.Options()

        msg = QMessageBox()

        fileTypes = ["Comma Separated Values (*.csv);;All Files (*)","MP4 (*.mp4);;All Files (*)"]

        directory = QFileDialog.getOpenFileName(self, "Open File", "", fileTypes[fileTypeIndex], options=options)

        if directory[0] != '':
      
            try:
                msg.setText("Successfully loaded file!")
                msg.setWindowTitle("Success")
                msg.exec()

                textBox.setPlainText(directory[0])

            except:
                msg.setText("Could not load Json file.")
                msg.setWindowTitle("Error")
                msg.exec()



if __name__ == "__main__":
    # Executes the app and configures a few small settings

    app = QApplication(sys.argv)

    app.setStyle('Fusion')

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        print('running in a PyInstaller bundle')
        stylesheet = loadFile(sys._MEIPASS + "/styles.qss")
    else:
        print('running in a normal Python process')
        stylesheet = loadFile("dev/styles.qss")

    app.setStyleSheet(stylesheet)
    
    window = MainWindow()
    
    window.show()

    sys.exit(app.exec())