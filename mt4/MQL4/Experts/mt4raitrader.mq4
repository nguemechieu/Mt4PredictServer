#include <sopotek/socket.mqh>


extern int port = 50052;
extern string ip_address = "127.0.0.1";

int listen_sock, msgsock;  // Global variable msgsock to be used across functions

// Function to process the received message and append "!!!!!"
string process(string inputs) {
    return (inputs + "!!!!!");
}

// Function to convert the buffer array to a string
string buffer_to_string(int &buffer[], int length) {
    string result = "";
    for (int i = 0; i < length; i++) {
        result += CharToString(buffer[i]);  // Convert each integer value to a character
    }
    
    return result;
}

// Function to handle the server loop that accepts a connection and processes messages
int start_server_loop(int socket) {
    msgsock = accept_connection(socket);  // Use the global msgsock for client connection

    if (msgsock == INVALID_SOCKET) {
        Print("Failed to accept client: ", WSAGetLastError());
        return -1;
    }

    // Loop to continuously receive messages from the client
    while (!IsStopped()) {
        int buffer[1024];  // Declare the buffer array for receiving data
        int received_length = receive_data(msgsock, buffer, ArraySize(buffer));

        if (received_length == SOCKET_ERROR) {
            Print("Receive failed: ", WSAGetLastError());
            break;
        }

        // Convert the received buffer to a string
        string message = buffer_to_string(buffer, received_length);
        string response = process(message);

        // Allocate a uchar array large enough to hold the response string
        uchar send_buffer[];
        ArrayResize(send_buffer, StringLen(response));  // Resize the buffer to fit the string length

        // Convert the response string to a uchar array (bytes)
        StringToCharArray(response, send_buffer);

        // Send the response back to the client
        int send_result = send_data(msgsock, send_buffer, ArraySize(send_buffer));
        if (send_result == SOCKET_ERROR) {
            Print("Send failed: ", WSAGetLastError());
            break;
        }
    }

    close_socket(msgsock);  // Close the client socket after communication
    return 0;
}

int init() {
    // Manually construct the sockaddr_in structure as an array
    int addr[6];  // Array to hold sockaddr_in values (sin_family, sin_port, sin_addr, sin_zero)

    // Fill sockaddr_in values
    addr[sin_family] = AF_INET;  // Address family (IPv4)
    addr[sin_port] = htons(port); // Convert port number to network byte order
    addr[sin_addr] = inet_addr(ip_address); // Convert IP address string to numeric form

    // Create the listening socket
    listen_sock = create_socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listen_sock == INVALID_SOCKET) {
        Print("Socket creation failed: ", WSAGetLastError());
        return -1;
    }

    // Bind the socket to the specified IP address and port
    if (bind(listen_sock, addr, ArraySize(addr)) == SOCKET_ERROR) {
        Print("Bind failed: ", WSAGetLastError());
        return -1;
    }

    // Start listening for incoming connections
    if (listen(listen_sock, SOMAXCONN) == SOCKET_ERROR) {
        Print("Listen failed: ", WSAGetLastError());
        return -1;
    }

    Print("Server is listening on ", ip_address, ":", port);

    // Start the server loop to accept and process client connections
    msgsock = start_server_loop(listen_sock);
    return INIT_SUCCEEDED;
}

// Deinit function that is called when the script is removed or stopped
int deinit() {
    if (msgsock != INVALID_SOCKET) {
        close_socket(msgsock);  // Close the client socket if valid
    }
    if (listen_sock != INVALID_SOCKET) {
        close_socket(listen_sock);  // Close the listening socket if valid
    }
    cleanup_winsock();  // Clean up Winsock resources
    Print("DEINIT");
    return 0;
}
