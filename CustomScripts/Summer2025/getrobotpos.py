import rtde_receive

rtde_receive = rtde_receive.RTDEReceiveInterface("10.241.34.45")
print(rtde_receive.getActualTCPPose())
