import sys
import socket,time

HOST = "10.241.34.47" #Mary IP
PORT = 30002 #Communication port
RETRIES = 10 #Number of tries to connect

def load_cnc_prog_num(prog_num):
    cmd = f"global cnc_prog_num = {prog_num}\n" #command to send to Mary
    for attempt in range(1, RETRIES+1):
        try:
            with socket.create_connection((HOST, PORT), timeout=3.0) as s: #Create a connection
                s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) #Check if connection is established
                s.settimeout(2.0)
                try:
                    _ = s.recv(1024) #Check if anything is received 
                except socket.timeout:
                    pass  
                #Once received and established connection is present
                s.sendall(cmd.encode("utf-8")) #send command to Mary through socket
                try:
                    s.shutdown(socket.SHUT_WR) #shutdown connection
                except OSError:
                    pass
                return True
        except (socket.timeout, OSError) as e: #if connection failed to create
            time.sleep(0.5 * attempt) #wait a few seconds
            with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\mary_connection_log.txt", "a") as file:
                file.write(f"Attempt {attempt}/{RETRIES}: {e}\n") #log into mary_connection_log.txt for visual inspection
    

if __name__ == "__main__":
    if len(sys.argv) > 1:
        load_cnc_prog_num(int(sys.argv[1])) #call load_cnc_prog_num using the argument passed from the parent function (_mesDynamicMachiningInit.py)   