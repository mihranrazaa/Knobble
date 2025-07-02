# Knobble
A modern design for not so common radios.

---

# Overview

Knobble is a Rasberry pi based portable Radio scanning system design for real time monitoring and interacting with different radio frequncies via an RTL-SDR dongle. It can help you to listen through FM, aviation, emergency, amateur, and public service frequencies.

---

## Features

- Runs on Rasberry PI zero 2 W.
- Multi-band scanning across FM, aviation, emergency, amateur, and police frequencies
- Preset system with multiple frequency banks and persistent storage.
- Automatic and manual scan modes
- Better shutdown process
- Oled Display for sharing all the relevant live info.
- and a cool CAD Design for emotional support lol.

---

## Controls

| Control                   | Action                                         |
| ------------------------- | ---------------------------------------------- |
| **Rotate Encoder**        | Adjust volume or frequency                     |
| **Encoder Button (tap)**  | Start/stop scanning                            |
| **Encoder Button (hold)** | Toggle mute/unmute                             |
| **Switch 1**              | Cycle through preset banks                     |
| **Switch 2**              | Toggle scan mode (Manual / Auto / Preset)      |
| **Switch 3**              | Change radio service type (FM, Aviation, etc.) |

---

## Files to build 

### PCB 

The files for the PCB and Schematics are available in the PCB folder and gerber files are added in the Production folder..

![Screenshot](Assets/npcb3d.png)

![Screenshot](Assets/npcb3d2.png)

### 3D Case (CAD)

The step files for the keyboard are available in the CAD folder and also in the Production Folder.

**BASE**

![Screenshot](Assets/ncad4.png)


**TOP**

![Screenshot](Assets/ncad5.png)


---

## Combined Images

![Screenshot](Assets/ucad3.png)

![Screenshot](Assets/ncad.png)

![Screenshot](Assets/ncad2.png)

![Screenshot](Assets/ncad3.png)


Can't add a combine image of pcb with components my laptop can't handle all that together..
Other than this you just have to purchase the Components given in the BOM and solder and assemble them.

---

## BOM 


| Component             | Quantity | Note                                                | Price      | Link                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --------------------- | -------- | --------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rasberry pi zero 2 w  | 1        | Controlling UNIT                                    | 16USD      | [Available](https://amzn.in/d/c275gW4)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| RTL-SDR               | 1        | most important for the project..                    | 51USD     | [Available](https://www.fabtolab.com/rtl-sdr-blog-v4-r828d-rtl2832u-1ppm-tcxo-sma-software-defined-radio-dipole-antenna-kit?search=RTL-SDR%20Blog)                           |
| 1.3 inch oled display | 1        | It has 2 extra Stabilizers just in case..           | 12USD       | [Available](https://www.amazon.in/OLED-Display-display-module-Blue/dp/B094W7TDKG/ref=sr_1_2?crid=3Q8FJIB11QGHE&dib=eyJ2IjoiMSJ9.B7UJuX2tN4RE5qUC46uLygug8WxLWjSOgkyJMu7-EXH34VlmGjoBuWPJP22TIlHrdvHc4LjgYXnp2hc3py_BE1EeIB7uhaHjrsFRpNXUNRdJJqR5dObtouw747pxiRkK7KSuLolsob9jHVAnGcaUQn5teiI1JISdhIaT3GLy4wLR4472yi4Cjp-WcG2tbnTWI6ai3V6rmwGP0F4cLP8XCu0CnJj878OKKMi18kqWd-w.z5miULqVkwuwROpuzjmyTGVz6pdf8Er0rOkTBH4zD-s&dib_tag=se&keywords=1%2C3+inch+oled+display&qid=1750676109&sprefix=1%2C3+inch+oled+displa%2Caps%2C227&sr=8-2) |
| macro switches        | 3        | user input they are 50 pcs the link i have provided | 0.9USD     | [Available](https://amzn.in/d/1zYgQJ0)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Rotary encoder        | 1        | User input                                          | 0.9USD     | [Available](https://amzn.in/d/8Zozbdr)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| PCM5102A DAC          | 1        | For connecting external speaker, headphones, etc    | 26USD      | [Available](https://amzn.in/d/7MQeXHS)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| UPS Hat               | 1        | For portability                                     | 26USD      | [Available](https://hubtronics.in/ups-hat-c)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| PCB                   | **       | JLCPCB ftw                                          | -          |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| CAD                   | **       | Legion ftw                                          | -          |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Total                 |          |                                                     | 135-145USD |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |


**I know it going above 150USD so i'm ready to pay the remaining cost...**

---

## Next Update 

- I want to add offline music listening...

---

## Extra Stuff

### Gratitude
- Thanks to Hackclub and Hackpad for making me do this brilliant project, More coming :).
- Thanks to my potato for helping me till the end.
- Thanks to myself for completing the project and not getting distracted with another project.
- And Thank you for Reading?

### Inspiration
**Going to Undercity!!** and i always wanted to build thiss project becuase RF always makes me curious it is like another invisible world which we can only access through speacial gears feels Magical...

### Challanging
Building the custom case.. i don't have the words to express my pain...

---

## End
Check my [BLOG](https://mihranrazaa.pages.dev/)
~ mihranrazaa(If you are reading this please review HappyUSB too ToT )

BYEEE
