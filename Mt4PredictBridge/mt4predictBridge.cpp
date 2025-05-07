#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <string>
#include <cstring>

#pragma comment(lib, "ws2_32.lib")

extern "C" __declspec(dllexport) void __stdcall PredictSignal(double ema_fast, double ema_slow, double rsi, char *result, int resultSize)
{
    WSADATA wsaData;
    SOCKET sock = INVALID_SOCKET;
    struct sockaddr_in server;
    char recvBuf[128] = {0};

    char message[64];
    sprintf_s(message, sizeof(message), "%.5f,%.5f,%.2f", ema_fast, ema_slow, rsi);

    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0)
        return;

    sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET)
    {
        WSACleanup();
        return;
    }

    server.sin_family = AF_INET;
    server.sin_port = htons(9999);
    inet_pton(AF_INET, "127.0.0.1", &server.sin_addr);

    if (connect(sock, (sockaddr *)&server, sizeof(server)) == SOCKET_ERROR)
    {
        closesocket(sock);
        WSACleanup();
        return;
    }

    send(sock, message, strlen(message), 0);
    int bytes = recv(sock, recvBuf, sizeof(recvBuf) - 1, 0);

    if (bytes > 0)
    {
        recvBuf[bytes] = '\0';
        strncpy_s(result, resultSize, recvBuf, _TRUNCATE);
    }

    closesocket(sock);
    WSACleanup();
}
