import os
import socket
import threading

from main import DetectionThread


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        # Create a socket object

        # Bind the socket to a specific address and port
        self.server_socket.bind((self.host, self.port))

        # Listen for incoming connections
        self.server_socket.listen(2)

        print(f"Server started. Waiting for connections to backend host {self.host}...")

        while True:
            # Accept a connection from a client
            client_socket, client_address = self.server_socket.accept()

            # Add the client to the clients dictionary
            self.clients[client_address] = client_socket

            print(f"New connection from {client_address}")

            detection_thread = DetectionThread(client_socket)
            detection_thread.start()

            # Start a new thread to handle the client's requests
            threading.Thread(target=self.handle_client, args=(client_socket, client_address, detection_thread)).start()

    def handle_client(self, client_socket, client_address, detection_thread):
        while True:
            # Receive data from the client
            data = client_socket.recv(1024)

            if not data:
                detection_thread.stop()
                client_socket.close()
                print("no data, stopping")
                break

            # Send the received data to the other client
            for address, socket in self.clients.items():
                if socket != client_socket:
                    socket.sendall(data)

        # help(client_socket)
        # Remove the client from the clients dictionary
        print(f"{self.clients}")
        print(f'removing client {client_address}')
        del self.clients[client_address]

        # Close the client socket
        client_socket.close()

    def stop(self):
        for address, socket in self.clients.items():
            socket.close()

        self.clients.clear()
        self.server_socket.close()
        self.server_socket.shutdown(socket.SHUT_RDWR)
        print("Server stopped")


# Create a server object
host = "192.168.248.132"  # localhost
print(os.environ.keys())
print(f'{os.getenv('host_address')}')
print(f'{os.environ.get('host_address')}')
port = 2024
server = Server(host, port)
try:
    server.start()
except Exception as e:
    print(e)
    server.stop()
