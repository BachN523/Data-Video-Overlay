import csv

def saveAsButton(fileName,whatToSave,howToSave):
    # reusable saving function

    file = open(fileName, howToSave)
            
    file.write(whatToSave)

    file.close()


def loadFile(fileName):
    # same as saveAsButton but loads instead and returns what is loaded
    file = open(fileName, "r")
            
    returnData = file.read()

    file.close()

    return returnData


def csvLoader(fileName):

    with open(fileName, mode='r') as file:
        csvReader = csv.DictReader(file)

        dataList = []
        for row in csvReader:
            dataList.append(row)

    return dataList