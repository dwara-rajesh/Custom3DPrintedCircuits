import coreModule
from math import pi

filename = r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\DEMO2.json" #circuit being tested
coreModule.get_stock_height_offset(filename)
print(f"Stock height offset: {coreModule.STOCK_HEIGHT_OFFSET}")
coreModule.load_calibration_data() #obtain calibration data after calibration is complete
z_offset = -0.7
z_offset_in_m = z_offset/1000
z_origin_ink = coreModule.CALIBRATION_DATA['ink'][2] + coreModule.top_right_vise[2] + coreModule.STOCK_HEIGHT_OFFSET + z_offset_in_m#offset the origin by calibration data to avoid hitting the vise and stock height offset to avoid hitting stock
origin_in_m_ink = [coreModule.top_right_vise[0],coreModule.top_right_vise[1]-coreModule.admlviceblock_yoff,z_origin_ink, 0, pi, 0]
coreModule.rtde_control.moveL(origin_in_m_ink,speed=coreModule.precise)