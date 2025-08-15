import sys
import socket,time

HOST = "10.241.34.47"   # UR5 IP
PORT = 30002            # Secondary client
RETRIES = 10

def load_cnc_prog_num(prog_num):
    cmd = f"global cnc_prog_num = {prog_num}\n"
    for attempt in range(1, RETRIES+1):
        try:
            with socket.create_connection((HOST, PORT), timeout=3.0) as s:
                # TCP keepalive (platform-specific tunables can be added if needed)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                # Optional: read a few bytes to confirm we’re getting the robot’s state stream
                # (secondary interface streams binary state packets ~125 Hz; not required but sanity-checks connectivity)
                s.settimeout(2.0)
                try:
                    _ = s.recv(1024)  # ignore contents; just proves we’re connected to the UR stream
                except socket.timeout:
                    pass  # some controllers may not deliver immediately; not fatal

                # Send script line reliably
                s.sendall(cmd.encode("utf-8"))

                # Gracefully half-close our write side so kernel flushes immediately
                try:
                    s.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

                # (Without an application-level ACK, there is no positive confirmation here.)
                return True
        except (socket.timeout, OSError) as e:
            time.sleep(0.5 * attempt)  # simple backoff
            with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\mary_connection_log.txt", "w") as file:
                file.write(f"Attempt {attempt}/{RETRIES}: {e}\n")
    

if __name__ == "__main__":
    if len(sys.argv) > 1:
        load_cnc_prog_num(int(sys.argv[1]))    