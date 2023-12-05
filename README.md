# Chat server
Chat server is an project written in python. Using libraries django and channels its able to run server with open websocket connection. The point of the server is that running instance of Heavenland game client can connect to the chat server, send chat messages and the chat server will broadcast the chat message to all connected clients

## Features
- Http API endpoints to check availability and version of the server
- Websocket endpoint to send and receive JSON messages
    - ability to login using access token
    - ability to send message to the chat
    - ability to receive chat messages that other clients send
    - ability to request a chat message history

### Http API
**/api** - send an get request and receive a response with http status 200 if the server is available
```
curl --location --request GET 'https://{server_url}/api'
```
  
**/api/version** - request a version of the server
```
curl --location --request GET 'https://{server_url}/api/version'
```
JSON response
```json
{
    "api": "v1.0.1",
    "env": "PRODUCTION",
    "desc": "Websocket Server Python"
}
```
### Websocket Connection
connect on `wss://{server_url}/chat`, if the connection is open you are able to send JSON messages  
**Logging in**
request
```json
{
  "action": "login",
  "token": "HeavenlandAccessToken"
}
```
response success
```json
{
  "info": "connected"
}
```
response error
```json
{
  "error": "error message describing the error"
}
```
**sending messages to the chat**  
request
```json
{
  "action": "message",
  "message": "the text of the message send to the chat",
  "channel": "General"
}
```
*note that `channel` is optional, can be either string or int*
  
broadcasted response to all connected clients (including the one that send the message)
```json
{
  "user_id": "HL365393213667",
  "timestamp": 1666259380,
  "message": "text of the chat message",
  "channel": "General",
  "nickname": "Great Heavenland Hero"
}
```
*note that `timestamp` is unix time, and `channel` is optional thus may not be included in the response.*
  
**requesting chat message history**  
request
```json
{
  "action": "history",
  "limit": 1,
  "offset": 0
}
```
*note that `limit` is optional, if not included 10 is default value, and `offset` is optional, if not included 0 is default value. Also currently only last 100 messages are saved in the chat history, this can be configured in the setting file*
  
response
```json
{
  "history": [
    {
      "user_id": "HL365393213667",
      "timestamp": 1666259380,
      "message": "text of the chat message",
      "channel": "General",
      "nickname": "Great Heavenland Hero"
    }
  ]
}
```
## Development
**python**  
to run the server locally you need to install [python 3.9](https://www.python.org/downloads/), python package manager [pip](https://pip.pypa.io/en/stable/installation/), and all the packages listed in Pipfile in root of the project. To install the packages either install pipenv `pip install pipenv`, and then in root of the project `pipenv install`, or you can install the packages individually by running `pip install <package_name>`
  
**redis**  
to run the server, redis is also needed, although for local development its possible to set the server to use memory instead of redis (! not possible for production tho), for local development this is set by configuring `CHANNEL_LAYERS` in settings.

**running server locally**  
set this environment variable to point the server to the setting file
```
DJANGO_SETTINGS_MODULE=websocketserver.settings.dev
```
*note that `dev` - local development, `cloud_run` - deployed development server, `prod` - deployed production server*
  
then run the server by this command (in root of the project)
```
python .\manage.py runserver
```
## Deployment
deployment is done by bitbucket CI/CD, config is in the deployment folder  
the server is dockerized before deployment, dockerfile is included in the project repo

## Project structure
**deployment** - code for the bitbucket CI/CD  
**websockerserver** - main folder of the code for the server  
* **api** - folder containing code for the Http API endpoints  
* **heavenland** - folder containing code to connect to heavenland API, and describe custom exceptions  
* **settings** - folder containing setting files for all environments  
* **ws** - folder containing the code for the websocket endpoints  

**ws**
* **urls** - list of registered websocket urls on the server
* **chat_history** - file to implement logic of communication with redis to add/get/remove messages from chat history
* **consumers** - file to implement the class HLConsumer which holds logic for websocket endpoint /chat for in-game chat
* **minigames** - file to implement the class MinigameConsumer which holds logic for the websocket endpoints /minigame 

**bitbucket-pipelines.yml** - CI/CD script    
**docker-compose.yml** - docker config  
**dockerfile** - docker config  
**extreme-arch-ws.json** - credentials for deployment  
**manage.py** - main python file to start the server  
**pipfile** - pipenv file to list the required packages  
**pipfile.lock** - don't touch, pipenv internal file to check for dependencies  
