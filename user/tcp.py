
import network
import socket
import os, time

def network_use_wlan(is_wlan=True):
    if is_wlan:
        sta = network.WLAN(0)
        sta.connect("_root-yang_", "18420277393+-")
        print(sta.status())
        while sta.ifconfig()[0] == '0.0.0.0':
            os.exitpoint()
        print(sta.ifconfig())
        ip = sta.ifconfig()[0]
        return ip
    else:
        a = network.LAN()
        if not a.active():
            raise RuntimeError("LAN interface is not active.")
        a.ifconfig("dhcp")
        print(a.ifconfig())
        ip = a.ifconfig()[0]
        return ip

def client():
    network_use_wlan(True)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ai = socket.getaddrinfo("192.168.0.110", 27015)
    print("Address infos:", ai)
    addr = ai[0][-1]

    print("Connecting to:", addr)
    try:
        s.connect(addr)
    except Exception as e:
        s.close()
        print("Connection error:", e)
        return

    # 打开 2 次记事本
    for i in range(2):
        message = "open notepad"
        print("Sending:", message)
        s.sendall(message.encode())
        time.sleep(0.2)

    s.close()
    print("Connection closed.")

client()