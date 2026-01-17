import socket, struct, time, random, json

def get_server_status(address_str):
    timeout = 5
    # Default structure for the JSON output
    result = {
        "name": address_str,
        "online": False, 
        "version": None, 
        "uptime_seconds": 0, # Note: Actual uptime tracking requires a database
        "address": address_str
    }
    
    try:
        if ":" in address_str:
            target = (address_str.split(":")[0], int(address_str.split(":")[1]))
        else:
            target = (address_str, 19132)

        magic = b'\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x124Vx'
        packet = b'\x02' + struct.pack(">q", random.randint(5, 20)) + magic

        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(packet, target)
        
        data = sock.recvfrom(2048)[0]
        # MCPI status usually looks like: MCCP;[protocol];[version];[motd];...
        decoded = data[35:].decode('utf-8', errors='ignore').split(';')
        
        result["online"] = True
        result["version"] = decoded[2] if len(decoded) > 2 else "Unknown"
        result["name"] = decoded[3] if len(decoded) > 3 else address_str
        # Simulating uptime for the progress bar (e.g., 5 hours)
        result["uptime_seconds"] = 18000 
        
    except Exception:
        pass # result remains "online": False
    finally:
        try: sock.close()
        except: pass
            
    return result

if __name__ == "__main__":
    servers = ["mcpi.izor.in", "thebrokenrail.com", "beiop.net:19134"]
    all_data = [get_server_status(s) for s in servers]
    
    with open("status.json", "w") as f:
        json.dump(all_data, f, indent=4)