import numpy as np
import pandas as pd
from LE import loadFile


def parse(fileLocation):
    #loadedFile = loadFile(fileLocation)

    print("parse")

    testData = [
        {
            "Time": [949333,961180,972976,979980,992980],
            "MPH":  [9,9,9,10,11]
        },
        {
            "Time": [926087,938665,952983,962987,972978],
            "MPH":  [4,4,4,6,7]
        }
    ]

    return testData




if __name__ == "__main__":
    parse("100HZLOG - Copy.CSV")

'''
[
    {
        "Time": [],
        "Global Time": []
    },
    {
        "Time": [],
        "Global Time": []
    }
]
'''