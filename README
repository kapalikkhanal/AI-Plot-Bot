# AI Plot Bot

AI Plot Bot is an python application that connects to your 3D printer via USB and transforms AI-generated responses into physical plots. Ask a question, get a response from Google's Gemini AI, and watch as your 3D printer plots the answer on paper.

![AI Plot Bot Interface](https://raw.githubusercontent.com/kapalikkhanal/AI-Plot-Bot/main/screenshots/interface.png)

## Features

- **AI Integration**: Seamless integration with Google's Gemini AI for natural language responses
- **Real-time G-code Visualization**: Preview the plot before printing
- **Printer Control**: Direct control of your 3D printer's axis
- **Customizable Parameters**: Adjust text formatting, paper dimensions, and printing speeds
- **Progress Tracking**: Monitor your print with a real-time progress bar

## Requirements

- Python
- 3D printer with USB connectivity
- Google Gemini API key

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/kapalikkhanal/AI-Plot-Bot.git
   cd AI-Plot-Bot
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Add your Gemini API key:
   Open `main.py` and replace the placeholder in this line:
   ```python
   genai.configure(api_key='YOUR_API_KEY_HERE')
   ```

## Usage

1. Launch the application:
   ```bash
   python main.py
   ```

2. Connect to your 3D printer:
   - Enter the correct COM port (e.g., COM3)
   - Enter the baud rate (typically 115200)
   - Click "Connect"

3. Ask a question:
   - Type your question in the input field
   - Click "Generate Response"
   - Review and edit the AI's response if needed
   - Click on Update AI Response if you made any changes on original response

4. Prepare for printing:
   - Adjust the G-code parameters as needed
   - Click "Update G-code" to generate and visualize the plot
   - Check the visualization preview

5. Start the print:
   - Make sure your printer is ready with paper and pen mounted
   - Click "Start Print"
   - Monitor the progress through the progress bar
   - Click "Stop" to pause the print

   ![Printing Demo 1](https://raw.githubusercontent.com/kapalikkhanal/AI-Plot-Bot/main/screenshots/test_1.JPG)

   ![Printing Demo 2](https://raw.githubusercontent.com/kapalikkhanal/AI-Plot-Bot/main/screenshots/test_2.JPG)

## Parameters Explained

- **Line Length**: Maximum length of a line in mm
- **Line Spacing**: Vertical distance between lines in mm
- **Padding**: Distance from the paper edges in mm
- **Paper Width/Height**: Dimensions of your paper in mm
- **Font Size**: Size of the text (affects line density)
- **Z Height**: Height at which the pen touches the paper in mm
- **Z Speed**: Speed of Z-axis movement in mm/min
- **Travel Speed**: Speed of travel moves in mm/min
- **Write Speed**: Speed of writing moves in mm/min
- **Default values just work great.**

## Printer Setup

For optimal results:

1. Mount a pen to your 3D printer's extruder
2. Secure paper to your print bed with paper clippers
3. Adjust the Z-height parameter to ensure proper contact between the pen and paper

## Technical Details

AI Plot Bot uses:

- **Tkinter**: For the graphical user interface
- **PySerial**: For communicating with the 3D printer
- **Google Generative AI**: For generating responses
- **Matplotlib**: For visualizing the G-code
- **text-to-gcode**: For converting text to printable G-code

The application flow:
1. User asks a question
2. Gemini AI generates a response
3. Response is converted to G-code using text-to-gcode
4. G-code is visualized for preview
5. Upon confirmation, G-code is sent to the printer

## Troubleshooting

- **Connection Issues**: Ensure the correct COM port and baud rate are selected
- **Empty Responses**: Check your API key and internet connection
- **Plotting Problems**: Adjust the Z-height parameter for optimal pen pressure
- **Text Formatting**: Modify line length and spacing for better readability

## Credits

- [text-to-gcode](https://github.com/Stypox/text-to-gcode): For the text-to-gcode conversion library
- [Google Generative AI](https://ai.google.dev/): For the Gemini AI model

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Future Improvements

- Support for multiple printers
- Additional AI models
- More advanced text formatting options
- Support for drawing images and diagrams
- Saving and loading configurations