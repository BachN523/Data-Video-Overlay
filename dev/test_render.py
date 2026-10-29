import os, sys, time, unittest

devDir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, devDir)

from DataVideoOverlayBackend import buildComposite
from moviepy import VideoFileClip

dataDir = os.path.join(devDir, "data")
outputDir = os.path.join(devDir, "output")

csvPath = os.path.join(dataDir, "100HZLOG.CSV")
videoPath = os.path.join(dataDir, "IMG_0144.mp4")

# How much of the video to render
renderSeconds = 60


@unittest.skipUnless(os.path.exists(csvPath) and os.path.exists(videoPath), "sample files not found in dev/data")
class TestRender(unittest.TestCase):

    def test_renderFirstMinute(self):
        # Renders the first minute with every overlay to dev/output so it can be watched at full speed
        os.makedirs(outputDir, exist_ok=True)
        outputPath = os.path.join(outputDir, "first_minute.mp4")

        finalCompo = buildComposite(csvPath, videoPath)
        endTime = min(renderSeconds, finalCompo.duration)
        finalCompo = finalCompo.subclipped(0, endTime)

        start = time.time()
        # temp_audiofile_path keeps moviepy's temporary audio file out of the working directory
        finalCompo.write_videofile(outputPath, threads=os.cpu_count(), temp_audiofile_path=outputDir)
        print(f"\nRendered {endTime:.1f}s of video in {time.time() - start:.1f}s -> {outputPath}")

        self.assertTrue(os.path.exists(outputPath))

        rendered = VideoFileClip(outputPath)
        self.assertAlmostEqual(rendered.duration, endTime, delta=0.5)
        self.assertEqual(rendered.size, finalCompo.size)
        rendered.close()


if __name__ == "__main__":
    unittest.main()
