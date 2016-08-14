import network
import socket
import ujson
import uos
import ure

HTTP_RESPONSE_HEADER = """HTTP/1.1 200 OK
Connection: close
Server: IoTWiFi
Content-Type: text/html


"""

HTML_OPTION_TEMPLATE = """<option value="{0}">{0}</option>"""

DEFAULT_TITLE = 'Device Name Setup'
DEFAULT_SSID = 'MicroPythonIoT'
DEFAULT_PSK = '12345678'


def serve_ssid_page(networks, nic, title):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 80))
    sock.listen(0)

    keep_serving = True

    while keep_serving:
        conn, addr = sock.accept()
        request = conn.recv(1024)
        conn.sendall(HTTP_RESPONSE_HEADER)
        request = str(request)

        # See if we have any URL params
        params = ure.compile('ssid=(.*?)&psk=(.*?) HTTP')
        groups = params.search(request)

        try:
            ssid, psk = groups.group(1), groups.group(2)

            wifi_details = {
                'ssid': ssid,
                'psk': psk
            }

            # Try and connect
            start_network(wifi_details, nic)

            with open('wifi.json', 'w') as f:
                f.write(ujson.dumps(wifi_details))

            conn.close()
            keep_serving = False
            break
        except:
            print('There was an error')

        # And so if there is nothing else to do, we serve the page
        with open('iotwifi.htm', 'r') as html:
            page = html.read()
            select_values = ''
            for net in networks:
                select_values += HTML_OPTION_TEMPLATE.format(net)

            page = page.format(
                title=title,
                options=select_values
            )
            conn.send(page)
        conn.sendall('\n')
        conn.close()
        print('Connection closed')


def start_network(wifi_details, nic):
    nic = network.WLAN(network.STA_IF)
    nic.active(True)
    nic.connect(wifi_details['ssid'], wifi_details['psk'])


def get_nic(title=DEFAULT_TITLE, ssid=DEFAULT_SSID, psk=DEFAULT_PSK):
    # First off, scan the current WiFi networks
    nic = network.WLAN(network.STA_IF)
    nic.active(True)
    networks = nic.scan()
    nic.active(False)
    network_names = [x[0].decode('unicode') for x in networks]

    # Then check if there is an existing network configuration
    valid_config = True

    if valid_config:
        try:
            uos.stat('wifi.json')
        except:
            valid_config = False
            print('No existing wifi config found')

    # And then check if we can load it from the file
    if valid_config:
        try:
            with open('wifi.json', 'r') as f:
                wifi_details = ujson.loads(f.read())
        except:
            valid_config = False
            print('Wifi config file is not valid')

    # And then see if that network is around for us to talk to
    if valid_config:
        if wifi_details['ssid'] in network_names:
            # Try and connect
            try:
                start_network(wifi_details, nic)
                print('Connected!')
            except:
                valid_config = False
                print('Could not connect to configured network')
        else:
            valid_config = False
            print('Configured network not currently available')

    # And if there is still no network... start the AP.
    if not valid_config:
        nic = network.WLAN(network.AP_IF)
        nic.config(essid=ssid, password=psk,
                   authmode=network.AUTH_WPA_WPA2_PSK)

        serve_ssid_page(network_names, nic, title)

    return nic
