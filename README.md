# Funkadelephant Lights
This project develops a new light system for the Funkadelephant art car. 

## Setup and installation
To start with funky_lights, first download the code using git:

``` 
git clone https://github.com/pitzer/funky_lights.git
``` 
Before running any of the tools, we have to install required dependencies and the funky_lights package with common Python modules. All of this can be done by navigating to the main code directory and run setup.py using the following command:
``` 
cd funky_lights
pip install -e .
``` 
The -e runs the package installing in editable mode (dynamically) which automatically detects any changes you make to the code when developing, avoiding the need to continually re-install the package.

Once installed, you can check that it was successfully installed by running:
``` 
pip list
``` 
You should now see the funky_lights package as well as those listed in the requirements.txt in the listed packages.

## LED boards
Each LED segment is controlled by a small attiny85 based board. The software for the board is in [attiny/attiny.ino](attiny/attiny.ino) file.

For the board to function correctly, we need to set fuses with the correct values to set the clock to 16Mhz internal and to enable Brown-out detection. There is a way to set the correct clock with the Arduino IDE, but it doesn’t enable the brown out detector. We also program the UID into the EEPROM and lock it using the EESAVE fuse to it persists when we update the application firmware. 
Here is the full list of fuse bits we need to set:

| Fuse          | Fuse Bit      | Notes                                                             |
| ------------- | ------------- | ----------------------------------------------------------------- |
| LOW           | CKSEL1        |                                                                   |
| LOW           | CKSEL2        |                                                                   |
| LOW           | CKSEL3        |                                                                   |
| HIGH          | SPIEN         |                                                                   |
| HIGH          | BODLEVEL2     | BODLEVEL 100 configure the brown out detector to 4.3V             | 
| HIGH          | EESAVE        | Lock EEPROM so it doesn’t get erased when programming             |
| EXTENDED      | SELFPRGEN     | Allow bootloader to program the flash                             |   

The board uses a simple bootloader that will enable us to update the main application over serial versus requiring a programmer attached to the chip. The bootloader is entered whenever the chip is powered on and it requires sending the CMD_BOOTLOADER message to enter the main application. The bootloader and also the main application communicate at 9600 baud by default. Before sending LED commands we typically want to increase the baudrate to a higher value, which is done using the CMD_SERIAL_BAUDRATE message. All of this is abstracted away in Python using the following initialization command:
``` 
serial_port = connection.InitializeController(tty_device, baudrate=250000)
``` 
### Program bootloader, set fuses, and UID
To get a board ready for use, we need to program the bootloader, set fuses, and burn the UID to EEPROM. All of this can be done using the [burn.sh](bootloader/burn.sh) script. With the USB programmer still attached burn the bootloader using the following commands:
``` 
cd bootloader
SEGMENT_UID=217
./burn.sh $SEGMENT_UID
``` 
After burning the bootloader will start immediately and display the UID on the LEDs. It will also output some debug information on pin 2.
If all looks good, disconnect the USB ISP programmer.

### Program main application 
The main application is in [attiny.ino](attiny/attiny.ino) and the compiled hex file is in [build/attiny.hex](attiny/build/attiny.hex). If the ino file is changed a new hex file can be generated using the [make.sh](attiny/make.sh) command.
``` 
cd attiny
./make.sh
``` 
NOTE: do NOT use the Arduino IDE to compile ino file or avrdude to program the main application. This will remove the bootloader.

To program the main application, connect to the (LED) serial and run:
``` 
python flash_application.py
``` 
Note, flash_application will update the main application on all boards connected to the bus by default. Change the UID if only one boards should be updated.

## Light controller
The light conroller is the main app that generates patterns and distributes them to the LED boards over multiple serial connections. The light controller also sends the LED patterns over websockets to a visualization (see below).

To start the light controller:
``` 
cd controller
python main.py
``` 

### Adding basic patterns

Adding new patterns is very simple and involves creating a new Pattern class and adding it to the Light controller's configuration. Start by adding a new Python file with class derived from `Pattern` to the [controller/patterns](controller/patterns) directory. Here is an example of a pattern that cycles through a fixed palette of colors at a set rate and sets all segments to use this color.

```python 
from patterns.pattern import Pattern
import numpy as np

PALETTE_TROPICAL = np.array(
    [[242, 207, 51], [245, 112, 76], [32, 158, 179], [240, 167, 141]])


class SolidColorBlinkPattern(Pattern):
    def __init__(self):
        super().__init__()

        # The following members are options that can be overwritten when adding the pattern
        # to the pattern config.

        # Color palette to cycle through
        self.palette = PALETTE_TROPICAL

        # Frequency of color change (in Hz)
        self.fps = 0.5

    def initialize(self):
        """ This method gets called once when the pattern is first instantiated."""
        self.cumulative_delta = 1000  # set to an arbitrary high value
        self.current_color_index = 0
        pass

    def animate(self, delta):
        """ animate is called at every timestep the lights are updated. Here is where the colors 
            of the desired segments in self.segments should be updated.
        Args:
            delta: time in seconds since the last animation
        """

        # First check if it is time to cycle to the next color in the palette
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return

        # Cycle to the next color
        self.current_color_index = (
            self.current_color_index + 1) % self.palette.shape[0]
  
        # Update segments to use the new color. 
        # 
        # Each "Segment" represents a single LED light strip on the art car. We are planning to have
        # on the order 80 segments in the final configuration. The segments are configure in the 
        # light controller using the config/led_config.json files. self.segments is populated from this
        # file when the Pattern is initialized.
        # 
        # The color array in each Segment has one RGB entry per LED on the light strip. The main purpose 
        # the animate method is updating the color array. The Segment also has a unique id. This can be 
        # used to only update certain segments during the animation. The CSV files in the config directory 
        # and the https://docs.google.com/spreadsheets/d/1Ga7npntoar6uwUSJpEfCIg9-kc4bZ1iFmo08Xg21sjo
        # and config/bus_config.all.json can be helpful to understand which segments belong to which part 
        # of the elephant, e.g. [1, 2, 3] are the three long strips going over the dome front to back.
        for segment in self.segments:
            for color in segment.colors:
                np.copyto(color, self.palette[self.current_color_index])

        # Reset time
        self.cumulative_delta = 0
``` 

Next add the pattern to the `DEFAULT_CONFIG` in [controller/patterns/pattern_config.py](controller/patterns/pattern_config.py). The `dict()` option allows you to overwrite any parameter members defined in `__init__`.

```python
from patterns.solid_color_blink import SolidColorBlinkPattern, PALETTE_TROPICAL

DEFAULT_CONFIG = [
    (SolidColorBlinkPattern, dict(palette=PALETTE_TROPICAL))
]
```

Run the light controller with the commands above and use the Visualization to see how it looks!

### Adding UV mapped patterns

Another cool way of defining patterns is by creating an animation in a 2D frame and UV map the lights into this frame using their 3D positions. This essentially results in an effect where the lights are treated as a screen and the animation projects images onto the screen. 

Here is an example of this using the `FirePatternUV` pattern implemented in https://github.com/pitzer/funky_lights/pull/16
 
![Screen Shot 2022-08-03 at 11 06 51 PM](https://user-images.githubusercontent.com/1485919/182775005-9145cae8-6b32-494b-ab35-ff427949321b.png)

Another example is the `VideoPattern` in [controller/patterns/video_pattern.py](controller/patterns/video_pattern.py)


## Visualization
To rapidly develop light patterns without any HW, we can use a 3D visualizer written in javasript and three.js. This web visualizer receives LED patterns from the light controller over websockets.

Run the 3D visualizer by starting a web server root directory of the code repository:
``` 
python -m http.server
``` 
Now point a browser to http://localhost:8000/visualization/three.js/editor 

Video of the visualization in action:

[![IMAGE ALT TEXT HERE](http://img.youtube.com/vi/MJFyqkiHWJo/0.jpg)](http://www.youtube.com/watch?v=MJFyqkiHWJo)

## Other docs

* Design doc: https://docs.google.com/document/d/193zCBdZJQ2zM1hZOcOoi2PbTF1X6veQUsoNvbH2qYzI/edit#heading=h.bk4r5cyiqgef
* Photos of Funkadelephant BEFORE the lights upgrades: https://photos.app.goo.gl/gXQorENS9bhVreZ16
* 3D Mesh files for the Funkadelephant art car: https://drive.google.com/drive/folders/1XdZmZc8DAyeh26kRkMO6nCtN7fgZzTzO?usp=sharing
