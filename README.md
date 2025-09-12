# Autonomous Manufacturing and Assembling of Custom 3D Printed Circuits  

## 📌 Overview  
This project focuses on developing an **autonomous small-scale manufacturing and assembly line** for custom 3D printed/machined circuits. The setup integrates milling machines, UR5 robotic arms, CAD/CAM automation, and an in-house MES (BUMES) to enable **scalable and flexible automated circuit production**.  

This system introduces students to automated manufacturing and assembly while pushing toward full autonomy.  

---

## 🛠 System Components  
- **2 Mills**: Paprika & Cayenne  
- **3 UR5 Robotic Arms**: Rosie, Mary & Edie  
- **Circuit Builder Application** (Python, Prototyped in Unity)  
- **Fusion 360 Add-ins** for Automated CAD & CAM  
- **Custom ADML Manufacturing Execution System (BUMES)**  

---

## 🚀 Project Goals  
1. **Circuit Builder Application** – Inspired by TinkerCAD, allowing users to design any circuit.  
2. **Automate CAD** – Generate CAD models automatically using Fusion 360 API.  
3. **Automate CAM** – Generate toolpaths and NC code automatically using Fusion 360 API.  
4. **ADML Integration** – Enable seamless machining, assembly, and ink tracing with robotic arms.  

---

## ✨ Features  
- **Circuit Builder Application**  
  - Add, delete, rotate, and connect components  
  - Save/load projects in `.json` format  
  - Easy component import and user customization  

- **Automated CAD & CAM**  
  - Load the project files directly into Fusion 360  
  - Auto-generate circuit geometry, pockets, and wire traces  
  - Automatic toolpath generation and NC file export  

- **ADML Integration**  
  - Full workflow: machining → pick-and-place → ink tracing  
  - Dynamic assembly with displacement-based checks  
  - Automated inventory tracking & restocking notifications  

---

## 🔬 Experiments & Results  
- Tested with **3 different circuit schematics** → successful dry-run integration.  
- Improved **PnP yield** with flexible resin vacuum grippers vs TPU.  
  - TPU 
    - Battery: 6/9  
    - Button: 7/8  
    - Microcontroller: 2/2  
    - LED: 12/20
  - Flex Resin
    - Battery: 9/9
    - Button: 8/8
    - Microcontroller: 2/2
    - LED: 15/20
- Pressure thresholds optimized per material:  
  - Flexible Resin: Battery (9.7), Button (9.7), Microcontroller (9.9), LED (10.89)  
  - TPU: Battery (6.5), Button (7.8), Microcontroller (6.5), LED (9.5)

---

## 📈 Advantages  
- Infinitely scalable circuit designs  
- Flexible assembly and ink tracing (relative waypoints, not fixed)  
- Minimal human involvement in CAD/CAM pipeline  
- Dynamic, modular, and efficient workflow  

---

## ⚠️ Limitations & Future Work  
- NC file sharing with mill still requires manual intervention (network issues).  
- Ink extrusion consistency needs refinement.  
- Future improvements:  
  - Multi-level undo in the circuit builder  
  - Integration with online component libraries  
  - Electrical connection simulation
  - MES simulation of the whole process
  - Visual inspection systems
  - Visual sensor integration
    - To allow for robot localization and traversal 

---

## 📷 Gallery  
Application, Automated CAD & CAM:<br>
https://drive.google.com/file/d/1Dc_Gp6TNuDpbt4n_A52WViqfs1KLvuOW/view?usp=drive_link<br>

Outputs (Assembly/Pick-N-Place):<br>
https://drive.google.com/file/d/1F0wVgRpb4WsJAGOhotOK_g7qnaFQ4t_g/view?usp=drive_link<br>
![machinedpiecesgit](https://github.com/user-attachments/assets/6bb27599-96c0-47f5-bc45-36459b41e17c)
![assembledgit](https://github.com/user-attachments/assets/c995fb4f-f565-4277-94ff-5b235d543600)

Outputs (Ink Tracing):
https://drive.google.com/file/d/10Jt-MQlTJDNQ9XNLLwXadmoF7CF8jco3/view?usp=drive_link

---


