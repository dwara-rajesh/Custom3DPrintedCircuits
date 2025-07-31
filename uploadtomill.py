import socket
import time

class HAASDNCStreamer:
    def __init__(self, mill_ip, port=5051):
        self.mill_ip = mill_ip
        self.port = port
        self.socket = None

    def connect(self):
        """Connect to HAAS DNC port"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.mill_ip, self.port))
            self.socket.settimeout(10)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def send_nc_file(self, file_path):
        """Stream NC file line by line"""
        if not self.socket:
            if not self.connect():
                return False

        try:
            with open(file_path, 'r') as file:
                for line_num, line in enumerate(file, 1):
                    # Clean up line
                    line = line.strip()
                    if not line or line.startswith(';'):  # Skip comments
                        continue

                    # Send line
                    self.socket.send((line + '\r\n').encode())

                    # Wait for acknowledgment (optional)
                    try:
                        response = self.socket.recv(1024).decode()
                        print(f"Line {line_num}: {line} -> {response.strip()}")
                    except socket.timeout:
                        print(f"Line {line_num}: {line} -> No response")

                    time.sleep(0.1)  # Small delay between lines

            return True

        except Exception as e:
            print(f"Error streaming file: {e}")
            return False

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None

# Usage
streamer = HAASDNCStreamer("192.168.1.101")
streamer.send_nc_file("my_program.nc")
streamer.disconnect()