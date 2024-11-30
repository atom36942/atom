#python
FROM python:3.12

#container working directory
WORKDIR /code

#copy requirements
COPY ./requirements.txt /code/requirements.txt

#install requirements
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#copy code to container working directory
COPY ./ /code

#run command
CMD ["python","main.py","--port", "80"]


