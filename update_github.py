
import requests
import subprocess
import time

def obtener_ngrok_url():

    while True:

        try:

            tunnels = requests.get(
                "http://127.0.0.1:4040/api/tunnels"
            ).json()

            url = tunnels["tunnels"][0]["public_url"]

            if "https://" in url:

                return url

        except:
            pass

        time.sleep(2)

def actualizar_github(url):

    with open("server.txt", "w") as f:

        f.write(url)

    subprocess.run("git add .", shell=True)
    subprocess.run('git commit -m "update url"', shell=True)
    subprocess.run("git push", shell=True)

if __name__ == "__main__":

    url = obtener_ngrok_url()

    print("NGROK URL:", url)

    actualizar_github(url)

    print("GitHub actualizado")