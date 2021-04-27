FROM  python:3.8-slim
# FROM  python:3.8-buster

## Main directory
WORKDIR /app

## Download license_plate.weights file
ADD https://onedrive.live.com/download?cid=4096C8A9EB1D4246&resid=4096C8A9EB1D4246%211338032&authkey=AAj07WGHXhheDKQ ./license_plate.weights


# ## Container Requirements
RUN apt-get update 
RUN apt-get install ffmpeg libsm6 libxext6  -y

## Copy only requirements files (better for Docker caching)
COPY requirements.txt /app/

## Install Python Requirements
RUN  pip install --upgrade pip && \
  pip install --use-deprecated=legacy-resolver -r requirements.txt

## Copy all files into /app directory
COPY . .

## Convert license_plate.weights file into tensorflow savedmodel format for use with tensorflow
RUN python save_model.py --weights ./license_plate.weights \
    --output ./models/license_plate-416 --input_size 416 --model yolov4 


RUN rm ./license_plate.weights

## These cmds be overided when addtional args are provided during runtime
CMD ["python", "app.py"]