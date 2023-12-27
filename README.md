# Aloha GUI
This is the gui for Aloha configuration visualizer.

### Run in pycharm
Create a conda environment with at least Python 3.5 and `pip install -r requirements.txt`.

Run `src/main/app.py` and then go to [http://0.0.0.0:8050/](http://0.0.0.0:8050/) in your preferred web browser.

### Docker
In the main Aloha directory where the Dockerfile is, run `docker build -t aloha-image:1.0 .` to build a Docker image named "aloha-image" version 1.0.

Then make a container and run it with `docker run -dp 8050:8050 aloha-image:1.0` and go to [http://0.0.0.0:8050/](http://0.0.0.0:8050/) in your preferred web browser.

### Docker Hints
* `docker images` to see all images.
* `docker image rm -f [image ID]` to delete image.
* `docker container ls -a` to see all containers.
* `docker container rm [container ID]` to delete container.
* `docker logs [container ID]` to see output logs.

### venv
1. `virtualenv --python="C:\Users\harnish\AppData\Local\Programs\Python\Python35\python.exe" myenv` or `python3 -m venv myenv` 
1. `source myenv\Scripts\activate`
1. `pip install -r requirements.txt`
1. `python src/main/app.py`