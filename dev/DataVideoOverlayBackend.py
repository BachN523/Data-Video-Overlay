import numpy as np
import pandas as pd
import os
os.environ["FFMPEG_BINARY"] = "ffmpeg/ffmpeg.exe"
os.environ["FFPLAY_BINARY"] = "ffmpeg/ffplay.exe"
from moviepy import *
from PIL import Image, ImageDraw


# https://youtu.be/8uGWXPqD8OA?si=ALAgcGJCDbM_9pUZ


def loadCSV(path):
    # Read CSV normally
    df = pd.read_csv(path)

    # Drop any rows where "Time" column is not numeric
    df = df[pd.to_numeric(df["Time"], errors="coerce").notna()].copy()

    # Convert types
    df["Time"] = df["Time"].astype(float) / 1_000_000
    df["MPH"] = df["MPH"].astype(float)
    df["RPM"] = df["RPM"].astype(float)
    df["throttle pos"] = df["throttle pos"].astype(float)
    df["Gear"] = df["Gear"].astype(float)
    df["VN Accel Lat"] = df["VN Accel Lat"].astype(float)
    df["VN Accel Long"] = df["VN Accel Long"].astype(float)

    # Keep only the columns we need
    return df[["Time", 
               "MPH", 
               "RPM", 
               "throttle pos", 
               "Gear",
               "VN Accel Lat",
               "VN Accel Long"]].reset_index(drop=True)


def dataAtTime(dataframe, t):
    times = dataframe["Time"].values
    speeds = dataframe["MPH"].values
    revs = dataframe["RPM"].values
    throttlepos = dataframe["throttle pos"].values
    gear = dataframe["Gear"].values
    accelLat = dataframe["VN Accel Lat"].values
    accelLong = dataframe["VN Accel Long"].values

    # 0 = MPH, 1 = RPM, 2 = Throttle Position, 3 = Gear
    return float(np.interp(t, times, speeds)), float(np.interp(t, times, revs)), float(np.interp(t, times, throttlepos)), float(np.interp(t, times, gear)), float(np.interp(t, times, accelLat)), float(np.interp(t, times, accelLong))


def roundedMask(size, radius):
    w, h = size

    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [(0, 0), (w, h)],
        radius=radius,
        fill=255
    )

    return np.array(img) / 255.0


def makeThrottleBar(df, videoDuration, width=300, height=20, color=(0, 255, 0)):

    times = df["Time"].values
    throttle_values = df["throttle pos"].values

    def make_frame(t):
        throttle = float(np.interp(t, times, throttle_values)) / 10

        bar_width = int((throttle / 100) * width)
        
        # Create a blank frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Fill in the bar
        frame[:, :bar_width] = color
        return frame

    clip = VideoClip(make_frame, duration=videoDuration)

    return clip


def makeClip(df, videoDuration, windowSize, fontSizeDivisionFactor, index, needsNeedle=False, imageLocation=None, label=None, conversionRate=1.5, baseValue=300, bgColor=None, horizontalAlign="center", verticalAlign="center", textAlign="left", cornerRoundness=None):
    
    def makeTextFrame(t, index, bgColor, horizontalAlign, verticalAlign, textAlign, mask=False):
        data = dataAtTime(df, t)

        if label != None:
            
            match index:

                case 3:
                                                        # If Gear is 0, display "N" for Neutral
                    txt = f"{label}:\n{int(data[index]) if int(data[index]) > 0 else 'N'}"

                case _:
                    txt = f"{label}:\n{int(data[index])}"

        else:
            txt = f"{int(data[index])}"


        text = TextClip(text=txt, 
                        font_size=(windowSize/fontSizeDivisionFactor), 
                        color="white",
                        method="caption", 
                        size=(windowSize,windowSize),
                        transparent=True,
                        bg_color=bgColor,
                        horizontal_align=horizontalAlign,
                        vertical_align=verticalAlign,
                        text_align=textAlign)
        

        return text.mask.get_frame(t) if mask else text.get_frame(t)
    
    
    def makeNeedle(t, index, conversionRate, baseValue, mask=False):
        needle = ImageClip("./dev/images/needle.png", False, True)
        needle = needle.with_duration(videoDuration)


        # Zero MPH is the needle rotated 300 degrees
        # 300           =  0 mph
        # 300 - 30      = 20 mph
        # 300 - 60      = 40 mph
        # 300 - 70      = 45 mph
        # 300 - 77      = 50 mph
        # 300 - 90      = 60 mph
        # 300 - 110     = 73 mph
        # 300 - 115.5   = 77 mph
        # 300 - 120     = 80 mph
        #ZEROMPH = 300

        #conversionRate = 1.5
        mph = dataAtTime(df, t)

        needle = needle.rotated(baseValue - (mph[index] * conversionRate))

        return needle.mask.get_frame(t) if mask else needle.get_frame(t)

    
    itemsToCompose = []


    if imageLocation != None:

        speedometer = ImageClip(imageLocation, False, True)

        speedometer = speedometer.with_duration(videoDuration)

        itemsToCompose.append(speedometer)


    mphText = VideoClip(lambda t: makeTextFrame(t, index, bgColor, horizontalAlign, verticalAlign, textAlign, mask=False), duration=videoDuration)
    mphTextMask = VideoClip(lambda t: makeTextFrame(t, index, bgColor, horizontalAlign, verticalAlign, textAlign, mask=True), duration=videoDuration, is_mask=True)

    if cornerRoundness != None:
        
        rounded = roundedMask((windowSize, windowSize), cornerRoundness)

        roundedClip = ImageClip(
            rounded,
            is_mask=True
        ).with_duration(videoDuration)

        mphText.mask = roundedClip

    else:
        mphText.mask = mphTextMask

    mphText = mphText.with_position((0,105))

    itemsToCompose.append(mphText)

    if needsNeedle:
        mphNeedle = VideoClip(lambda t: makeNeedle(t, index, conversionRate, baseValue, mask=False), duration=videoDuration)
        mphNeedleMask = VideoClip(lambda t: makeNeedle(t, index, conversionRate, baseValue, mask=True), duration=videoDuration, is_mask=True)

        mphNeedle.mask = mphNeedleMask

        itemsToCompose.append(mphNeedle)


    dynamicCompo = CompositeVideoClip(itemsToCompose)

    dynamicCompo = dynamicCompo.with_opacity(.58)

    return dynamicCompo



def backendMain(csvPath, videoPath):
    #pathOne is the CSV and pathTwo is the video

    returnArray = ["Title","Description"]

    if csvPath.strip() != "" and videoPath.strip() != "":
        print(csvPath, videoPath)

        loadedCSV = loadCSV(csvPath)

        video = VideoFileClip(videoPath)

        videoLength = video.duration

        video = video.with_duration(videoLength)

        windowSize = 500
        fontSizeDivisionFactor = 11.6

                                                                                 # 0 = MPH
        mph = makeClip(loadedCSV, videoLength, windowSize, fontSizeDivisionFactor, 0, True, "./dev/images/speedometer.png")

                                                                                 # 1 = RPM
        rpm = makeClip(loadedCSV, videoLength, windowSize, fontSizeDivisionFactor, 1, True, "./dev/images/tachometer.png", conversionRate=3.977, baseValue=315)


        throttleBar = makeThrottleBar(loadedCSV, video.duration, width=300, height=20, color=(255,0,0))
                                                                                            # Mizzou Gold: rgb(241, 184, 45)


                                                      # 3 = gear
        gear = makeClip(loadedCSV, videoLength, 250, 4, 3, label="Gear", bgColor="black", verticalAlign="top", textAlign="center", cornerRoundness=25)
        



        if video.aspect_ratio == 16/9:
            print("widescreen landscape")
            mph = mph.resized((370,370))
            rpm = rpm.resized((370,370))
            rpm = rpm.with_position((350,0))

            gear = gear.resized((150,150))
            gear = gear.with_position((300,200))
            

        elif video.aspect_ratio == 9/16:
            print("widescreen portrait")
            mph = mph.resized((350,350))
        
            rpm = rpm.resized((350,350))

            rpm = rpm.with_position((350,0))

            gear = gear.with_position((100,600))

        elif video.aspect_ratio == 4/3:
            print("Fullscreen\nWhy are you using 4:3 in the 2020s")
        

        finalCompo = CompositeVideoClip(
            [
                video,
                mph,
                rpm,
                throttleBar,
                gear
            ]
        )
        
        finalCompo.preview()

        #finalCompo.write_videofile("result.mp4")

        returnArray[0] = "Success!"
        returnArray[1] = "The video has finished rendering."

    else:
        returnArray[0] = "ERROR"
        returnArray[1] = "No file selected."

    return returnArray
    

if __name__ == "__main__":
    backendMain("100HZLOG.CSV", "IMG_0144.mp4")