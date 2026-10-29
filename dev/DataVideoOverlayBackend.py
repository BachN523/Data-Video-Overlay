import numpy as np
import pandas as pd
import os, sys

# Only point moviepy at a local ffmpeg if one is actually there, otherwise it uses its bundled ffmpeg
if os.path.exists("ffmpeg/ffmpeg.exe"):
    os.environ["FFMPEG_BINARY"] = "ffmpeg/ffmpeg.exe"
if os.path.exists("ffmpeg/ffplay.exe"):
    os.environ["FFPLAY_BINARY"] = "ffmpeg/ffplay.exe"

from moviepy import *
from PIL import Image, ImageDraw


# https://youtu.be/8uGWXPqD8OA?si=ALAgcGJCDbM_9pUZ


def imgPath(name):
    # Images live next to this file normally, and in sys._MEIPASS when running in a PyInstaller bundle
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "images", name)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", name)


# Columns the overlays need from the CSV
requiredColumns = ["Time",
                   "MPH",
                   "RPM",
                   "throttle pos",
                   "Gear",
                   "VN Accel Lat",
                   "VN Accel Long"]


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
    return df[requiredColumns].reset_index(drop=True)


def stepLookup(t, times, vals):
    # Holds the last logged value instead of interpolating (so gear never reads 2.4 mid-shift)
    return vals[np.clip(np.searchsorted(times, t, side="right") - 1, 0, len(vals) - 1)]


def columnArrays(dataframe):
    # Pull the columns out as numpy arrays once so dataAtTime doesn't redo it every frame
    return {column: dataframe[column].values for column in dataframe.columns}


def dataAtTime(columns, t):
    times = columns["Time"]
    speeds = columns["MPH"]
    revs = columns["RPM"]
    throttlepos = columns["throttle pos"]
    gear = columns["Gear"]
    accelLat = columns["VN Accel Lat"]
    accelLong = columns["VN Accel Long"]

    # 0 = MPH, 1 = RPM, 2 = Throttle Position, 3 = Gear
    return float(np.interp(t, times, speeds)), float(np.interp(t, times, revs)), float(np.interp(t, times, throttlepos)), float(stepLookup(t, times, gear)), float(np.interp(t, times, accelLat)), float(np.interp(t, times, accelLong))


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


def makeThrottleBar(df, videoDuration, width=300, height=20, color=(0, 255, 0), throttleMax=1000):
    # throttleMax is the logger's full-throttle reading

    times = df["Time"].values
    throttle_values = df["throttle pos"].values

    def make_frame(t):
        throttle = float(np.interp(t, times, throttle_values)) / throttleMax * 100
        throttle = min(max(throttle, 0), 100)

        bar_width = int((throttle / 100) * width)

        # Create a blank frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Fill in the bar
        frame[:, :bar_width] = color
        return frame

    clip = VideoClip(make_frame, duration=videoDuration)

    return clip


def makeGGMeter(df, duration, size=200, maxG=1.5, units_in_ms2=True, flipLat=False, flipLong=False):
    times = df["Time"].values
    scale = 9.81 if units_in_ms2 else 1.0
    lat = df["VN Accel Lat"].values / scale * (-1 if flipLat else 1)
    lon = df["VN Accel Long"].values / scale * (-1 if flipLong else 1)
    ringRadius = 48 / 100 * size
    ring = ImageClip(imgPath("gg.png")).resized((size, size)).with_duration(duration)
    dot = ImageClip(imgPath("ggDot.png")).resized((size, size)).with_duration(duration)
    def dotPos(t):
        gx = float(np.interp(t, times, lat)) / maxG
        gy = float(np.interp(t, times, lon)) / maxG
        mag = np.hypot(gx, gy)
        if mag > 1:
            gx, gy = gx / mag, gy / mag
        return (gx * ringRadius, -gy * ringRadius)  # accel up, braking down
    dot = dot.with_position(dotPos)
    return CompositeVideoClip([ring, dot], size=(size, size)).with_duration(duration).with_opacity(.58)


def makeClip(df, videoDuration, windowSize, fontSizeDivisionFactor, index, needsNeedle=False, imageLocation=None, label=None, conversionRate=1.5, baseValue=300, bgColor=None, horizontalAlign="center", verticalAlign="center", textAlign="left", cornerRoundness=None, textPosition=None):

    columns = columnArrays(df)

    # The displayed number changes far less often than the frame rate, so each string is only rendered once
    renderedText = {}

    def makeTextFrame(t, index, bgColor, horizontalAlign, verticalAlign, textAlign, mask=False):
        data = dataAtTime(columns, t)

        if label != None:

            match index:

                case 3:
                                                        # If Gear is 0, display "N" for Neutral
                    txt = f"{label}:\n{int(data[index]) if int(data[index]) > 0 else 'N'}"

                case _:
                    txt = f"{label}:\n{int(data[index])}"

        else:
            txt = f"{int(data[index])}"


        if txt not in renderedText:
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

            renderedText[txt] = (text.get_frame(0), text.mask.get_frame(0))


        return renderedText[txt][1] if mask else renderedText[txt][0]


    # Loaded once, only rotated per frame
    needle = ImageClip(imgPath("needle.png"), False, True)
    needle = needle.with_duration(videoDuration)

    # moviepy asks for the same needle frame several times per output frame (resize, opacity and mask
    # compositing each pull it), so keep the rotated image and mask for the current t
    rotatedFrames = {}

    def makeNeedle(t, index, conversionRate, baseValue, mask=False):
        if rotatedFrames.get("t") != t:
            rotatedFrames.clear()
            rotatedFrames["t"] = t

        if mask in rotatedFrames:
            return rotatedFrames[mask]


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
        mph = dataAtTime(columns, t)

        rotatedNeedle = needle.rotated(baseValue - (mph[index] * conversionRate))

        rotatedFrames[mask] = rotatedNeedle.mask.get_frame(t) if mask else rotatedNeedle.get_frame(t)

        return rotatedFrames[mask]


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

    # Default puts the readout in the lower part of the gauge, scaled to the window size
    if textPosition == None:
        textPosition = (0, int(windowSize * 0.21))

    mphText = mphText.with_position(textPosition)

    itemsToCompose.append(mphText)

    if needsNeedle:
        mphNeedle = VideoClip(lambda t: makeNeedle(t, index, conversionRate, baseValue, mask=False), duration=videoDuration)
        mphNeedleMask = VideoClip(lambda t: makeNeedle(t, index, conversionRate, baseValue, mask=True), duration=videoDuration, is_mask=True)

        mphNeedle.mask = mphNeedleMask

        itemsToCompose.append(mphNeedle)


    dynamicCompo = CompositeVideoClip(itemsToCompose, size=(windowSize, windowSize))

    dynamicCompo = dynamicCompo.with_opacity(.58)

    return dynamicCompo


def isAspectRatio(ar, target):
    return abs(ar - target) < 0.01


def buildComposite(csvPath, videoPath):
    # Builds the video with every overlay on it. Split out of backendMain so it can be tested without previewing
    loadedCSV = loadCSV(csvPath)

    video = VideoFileClip(videoPath)

    videoLength = video.duration

    video = video.with_duration(videoLength)

    windowSize = 500
    fontSizeDivisionFactor = 11.6

                                                                             # 0 = MPH
    mph = makeClip(loadedCSV, videoLength, windowSize, fontSizeDivisionFactor, 0, True, imgPath("speedometer.png"))

                                                                             # 1 = RPM
    rpm = makeClip(loadedCSV, videoLength, windowSize, fontSizeDivisionFactor, 1, True, imgPath("tachometer.png"), conversionRate=3.977, baseValue=315)


    throttleBar = makeThrottleBar(loadedCSV, video.duration, width=650, height=20, color=(255,0,0))
                                                                                        # Mizzou Gold: rgb(241, 184, 45)


                                                  # 3 = gear
    gear = makeClip(loadedCSV, videoLength, 250, 4, 3, label="Gear", bgColor="black", verticalAlign="top", textAlign="center", cornerRoundness=25, textPosition=(0,0))

    # The log records acceleration in G's, not m/s^2
    gg = makeGGMeter(loadedCSV, videoLength, size=200, units_in_ms2=False)


    ar = video.aspect_ratio

    if isAspectRatio(ar, 16/9):
        print("widescreen landscape")
        mph = mph.resized((370,370))
        mph = mph.with_position((0,0))

        rpm = rpm.resized((370,370))
        rpm = rpm.with_position((350,0))

        gear = gear.resized((150,150))
        gear = gear.with_position((300,200))

        throttleBar = throttleBar.with_position((35,380))

        gg = gg.with_position((740,85))


    elif isAspectRatio(ar, 9/16):
        print("widescreen portrait")
        mph = mph.resized((350,350))
        mph = mph.with_position((0,0))

        rpm = rpm.resized((350,350))
        rpm = rpm.with_position((350,0))

        gear = gear.resized((150,150))
        gear = gear.with_position((100,600))

        throttleBar = throttleBar.with_position((25,360))

        gg = gg.with_position((300,600))

    elif isAspectRatio(ar, 4/3):
        print("Fullscreen\nWhy are you using 4:3 in the 2020s")
        mph = mph.resized((370,370))
        mph = mph.with_position((0,0))

        rpm = rpm.resized((370,370))
        rpm = rpm.with_position((350,0))

        gear = gear.resized((150,150))
        gear = gear.with_position((300,200))

        throttleBar = throttleBar.with_position((35,380))

        gg = gg.with_position((740,85))

    else:
        print(f"Unrecognized aspect ratio {ar:.3f}, using the default layout")
        mph = mph.resized((370,370))
        mph = mph.with_position((0,0))

        rpm = rpm.resized((370,370))
        rpm = rpm.with_position((350,0))

        gear = gear.resized((150,150))
        gear = gear.with_position((300,200))

        throttleBar = throttleBar.with_position((35,380))

        gg = gg.with_position((740,85))


    finalCompo = CompositeVideoClip(
        [
            video,
            mph,
            rpm,
            throttleBar,
            gear,
            gg
        ]
    )

    return finalCompo


def backendMain(csvPath, videoPath):
    #pathOne is the CSV and pathTwo is the video

    returnArray = ["Title","Description"]

    if csvPath.strip() != "" and videoPath.strip() != "":
        print(csvPath, videoPath)

        finalCompo = buildComposite(csvPath, videoPath)

        finalCompo.preview()

        #finalCompo.write_videofile("result.mp4")

        returnArray[0] = "Success!"
        returnArray[1] = "Preview closed."

    else:
        returnArray[0] = "ERROR"
        returnArray[1] = "No file selected."

    return returnArray


if __name__ == "__main__":
    # The sample files sit next to this script, so build their paths from here to work from any directory
    devDir = os.path.dirname(os.path.abspath(__file__))
    backendMain(os.path.join(devDir, "100HZLOG.CSV"), os.path.join(devDir, "IMG_0144.mp4"))
