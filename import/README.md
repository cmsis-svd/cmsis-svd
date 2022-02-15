# Importing svd files from other sources

## Prerequisites
- Docker installed

### Intro
There are several repositories where native vendor data is converted into svd.
Example: [Texas Instrumnets MSP430 series](https://github.com/pftbest/msp430_svd)

### Starting the container
Open a cmd to this folder. Edit the volume that must be mounted inside the container.  
The volume is the folder where the downloaded repository is.
Start the container: 
```
docker-compose up -d
```

### Running a shell inside the container
Run
```
docker exec -it <mycontainer> bash
```
where <mycontainer> is a part of the container id obtained by ```docker ps```

### Converting
Follow the instructions given by the repository. Do not forget to rename and formatting the resulting svd, and place it in the correct data folder.