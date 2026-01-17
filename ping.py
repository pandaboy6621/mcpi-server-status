import socket, struct, time, random, json

def chechubben(server):
    timeout = 5
    result = {"address": server, "status": "Offline", "name": None}
    
    try:
        if ":" in server:
            targetServer = (server.split(":")[0], int(server.split(":")[1]))
        else:
            targetServer = (server, 19132)

        magicCrap = b'\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x124Vx'
        pingPacket = b'\x02' + struct.pack(">q", random.randint(5, 20)) + magicCrap

        udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        udp_socket.settimeout(timeout)
        udp_socket.sendto(pingPacket, targetServer)
        
        data = udp_socket.recvfrom(2048)[0]
        len_val = ord(data[34:34 + 1])
        serverName = data[35:35 + len_val].decode('utf-8').split(';')[2]
        
        result["status"] = "Online"
        result["name"] = serverName
        print(f"Success: {server} is {serverName}")
        
    except socket.timeout:
        print(f"Timeout: {server}")
    except Exception as e:
        print(f"Error pinging {server}: {e}")
    finally:
        try:
            udp_socket.close()
        except:
            pass
            
    return result

if __name__ == "__main__":
    servers_to_ping = [
        "mcpi.izor.in",
        "thebrokenrail.com",
        "beiop.net:19134",
        "beiop.net:19135",
        "beiop.net:19136"
    ]

    all_results = []
    for s in servers_to_ping:
        all_results.append(chechubben(s))

    # Save the list of results to status.json
    with open("status.json", "w") as f:
        json.dump(all_results, f, indent=4)
    
    print("\nResults saved to status.json")